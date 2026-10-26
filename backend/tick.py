"""A6 调度 tick:表驱动(AIHOT 模式)——只处理 next_fetch_at 到期的源

链路:抖音自数据(每日)→ 素材抓取(每日)→ 报告自动生成(每周,且 LLM 可用时)。
幂等:可由 Windows 任务计划每天触发;不到期就空转退出(秒级)。
通知:health 变 failing 时写 data/alert.flag(推送通道待拍板 Server酱/飞书后接入)。
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from . import db, ingest, llm, materials, report
from .config import BJ_TZ, ROOT


def _ensure_source(sid: str, name: str, kind: str, interval_minutes: int) -> None:
    db.conn().execute(
        """INSERT INTO sources(id, name, kind, interval_minutes, updated_at)
           VALUES(?,?,?,?,'') ON CONFLICT(id) DO NOTHING""",
        (sid, name, kind, interval_minutes),
    )
    db.conn().commit()


def _due(sid: str, now) -> bool:
    r = db.conn().execute("SELECT next_fetch_at, enabled FROM sources WHERE id=?", (sid,)).fetchone()
    if not r or not r["enabled"]:
        return False
    nxt = r["next_fetch_at"]
    return (not nxt) or now >= datetime.fromisoformat(nxt)


def _mark_next(sid: str, interval_minutes: int) -> None:
    from datetime import timedelta

    nxt = (datetime.now(tz=ZoneInfo(BJ_TZ)) + timedelta(minutes=interval_minutes)).isoformat(timespec="seconds")
    db.conn().execute("UPDATE sources SET next_fetch_at=?, updated_at=? WHERE id=?", (nxt, db.now_iso(), sid))
    db.conn().commit()


def tick() -> None:
    db.init_db()
    now = datetime.now(tz=ZoneInfo(BJ_TZ))
    _ensure_source("douyin_self", "抖音自数据(douyin-mcp)", "douyin_self", 1440)
    _ensure_source("materials_hub", "素材引擎(知乎/微博/一言)", "materials", 1440)
    _ensure_source("report_weekly", "周报生成(LLM)", "report", 10080)
    _ensure_source("bench_scripts", "爆款脚本管线(对标逐字稿)", "scripts", 10080)

    # ---- 抖音自数据 ----
    if _due("douyin_self", now):
        print("[tick] douyin_self:到期,开始同步…")
        result = ingest.run_douyin_sync()
        _mark_next("douyin_self", 1440)
        print(f"[tick] douyin_self 完成:{result}")
    else:
        print("[tick] douyin_self:未到期,跳过")

    # ---- 素材抓取(每日)----
    if _due("materials_hub", now):
        print("[tick] materials_hub:到期,抓取素材…")
        try:
            r = materials.fetch_and_score()
            print(f"[tick] 素材完成:{r}")
        except Exception as e:  # noqa: BLE001
            print(f"[tick] 素材抓取失败:{e}")
        _mark_next("materials_hub", 1440)

    # ---- 周报(每周,LLM 可用时才自动,避免降级版刷屏)----
    if _due("report_weekly", now) and llm.llm_configured():
        print("[tick] report_weekly:到期,生成报告…")
        try:
            r = report.generate()
            print(f"[tick] 报告完成:{r}")
        except Exception as e:  # noqa: BLE001
            print(f"[tick] 报告生成失败:{e}")
        _mark_next("report_weekly", 10080)

    # ---- 爆款脚本管线(每周:对标爆款 → 逐字稿 → 素材库)----
    if _due("bench_scripts", now):
        print("[tick] bench_scripts:到期,提取爆款脚本…")
        try:
            from . import scripts_ingest
            r = scripts_ingest.ingest_bench_scripts(limit=3)
            print(f"[tick] 脚本管线完成:{r}")
        except Exception as e:  # noqa: BLE001
            print(f"[tick] 脚本管线失败:{e}")
        _mark_next("bench_scripts", 10080)

    # 告警标记(P1 用文件标记,推送通道接入后替换为真实推送)
    failing = db.conn().execute(
        "SELECT id, last_error FROM sources WHERE health='failing'"
    ).fetchall()
    flag = ROOT / "data" / "alert.flag"
    if failing:
        flag.write_text(
            "\n".join(f"{r['id']}: {r['last_error']}" for r in failing), encoding="utf-8"
        )
        print(f"[tick] 告警:{len(failing)} 个源 failing,已写 {flag.name}")
    elif flag.exists():
        flag.unlink()
        print("[tick] 全部恢复,告警标记已清除")


if __name__ == "__main__":
    tick()
