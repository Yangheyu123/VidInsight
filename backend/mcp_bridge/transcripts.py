"""MCP 桥接:douyin-mcp 转写通道(运行于 vendors venv,由 backend/own_transcripts.py 子进程调起)

职责:提交近期作品转写任务 → 轮询至完成 → 拉取逐字稿 → stdout 输出 JSON
环境由调用方注入:TRANSCRIPT_INGESTION_ENABLED / FFMPEG 路径 / HF_ENDPOINT
"""
import asyncio
import json
import sys


def _d(tool_result):
    """fastmcp CallToolResult → dict(取 data 或 content 文本解析)"""
    if hasattr(tool_result, "data") and tool_result.data is not None:
        return tool_result.data if isinstance(tool_result.data, dict) else {"raw": str(tool_result.data)}
    if hasattr(tool_result, "content") and tool_result.content:
        text = "".join(getattr(c, "text", "") for c in tool_result.content)
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {"raw": text[:500]}
    return {"raw": str(tool_result)[:500]}


async def main(limit: int) -> None:
    from fastmcp import Client

    from douyin_creator_mcp.server import create_mcp

    mcp = create_mcp()
    async with Client(mcp) as c:
        # 1) 提交转写任务(近期 N 条)
        sub = _d(await c.call_tool("douyin_browser_submit_transcript_run", {"recent_limit": limit}))
        run_id = sub.get("run_id") or (sub.get("run") or {}).get("id") or sub.get("id")
        print(f"[bridge] run_id={run_id} status={sub.get('status')}", file=sys.stderr)

        # 2) 轮询(≤10 分钟;worker 在本进程内,Client 必须保持打开)
        final = sub
        if run_id is not None:
            for _ in range(120):
                await asyncio.sleep(5)
                final = _d(
                    await c.call_tool("douyin_browser_get_transcript_run", {"run_id": run_id})
                )
                status = str(final.get("status") or (final.get("run") or {}).get("status") or "")
                if status.lower() in ("completed", "failed", "cancelled", "done"):
                    break
        print(f"[bridge] final={str(final)[:300]}", file=sys.stderr)

        # 3) 作品清单 + 逐字稿(分页拼接,含 raw_text)
        vids = _d(await c.call_tool("douyin_browser_list_videos", {"limit": limit}))
        videos = vids.get("videos") or []
        out = []
        for v in videos:
            vid = v.get("id") or v.get("video_id")
            if not vid:
                continue
            parts: list[str] = []
            cursor = None
            for _page in range(10):  # ≤10 页,防失控
                tr = _d(
                    await c.call_tool(
                        "douyin_browser_get_video_transcript",
                        {"video_id": vid, "limit": 100, "include_raw_text": True, **({"cursor": cursor} if cursor else {})},
                    )
                )
                segs = tr.get("segments") or tr.get("items") or tr.get("shards") or []
                for s in segs:
                    if isinstance(s, dict):
                        parts.append(s.get("raw_text") or s.get("text") or "")
                if not segs and not parts:
                    parts.append(tr.get("raw_text") or tr.get("text") or "")
                cursor = tr.get("next_cursor") or tr.get("cursor")
                if not cursor:
                    break
            text = "".join(parts).strip()
            out.append(
                {
                    "video_id": vid,
                    "title": v.get("title"),
                    "publish_time": v.get("publish_time"),
                    "transcript": text,
                    "transcript_chars": len(text),
                }
            )
        json.dump({"run_id": run_id, "final_status": final.get("status"), "videos": out}, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 2))
