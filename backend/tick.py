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

    # ---- P0 备份:每日滚动备份 platform.db(保留 7 份) ----
    try:
        import shutil
        import sqlite3

        backup_dir = ROOT / "data" / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d")
        dest = backup_dir / f"platform-{stamp}.db"
        if not dest.exists():
            src = sqlite3.connect(ROOT / "data" / "platform.db")
            dst = sqlite3.connect(dest)
            src.backup(dst)
            dst.close()
            src.close()
        olds = sorted(backup_dir.glob("platform-*.db"))
        for old in olds[:-7]:
            old.unlink(missing_ok=True)
        print(f"[tick] 备份 OK:{dest.name}")
    except Exception as e:  # noqa: BLE001
        print(f"[tick] 备份失败:{e}")

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
        # 顺带:本地产线脚本采集(纯本地文件解析,秒级)
        try:
            from . import own_scripts

            print(f"[tick] 产线脚本: {own_scripts.harvest_own_scripts()}")
        except Exception as e:  # noqa: BLE001
            print(f"[tick] 产线脚本采集失败:{e}")
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
            # 报告完成 → 自动刷新产线创作简报(闭环最后一跳)
            from . import brief

            print(f"[tick] 创作简报: {brief.build_brief()}")
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
            cr = scripts_ingest.ingest_bench_comments(limit_videos=2)
            print(f"[tick] 爆款评论:{cr}")
        except Exception as e:  # noqa: BLE001
            print(f"[tick] 脚本管线失败:{e}")
        _mark_next("bench_scripts", 10080)

    # ---- 对标雷达(每周:扫「关键词订阅表」里启用的关键词,B站+YouTube)----
    if _due("radar_bench", now):
        print("[tick] radar_bench:到期,按订阅关键词扫描…")
        kws = db.conn().execute(
            "SELECT id, platform, keyword FROM radar_keywords WHERE enabled=1"
        ).fetchall()
        if not kws:
            print("[tick] 订阅表为空,跳过(界面添加关键词后生效)")
        for k in kws:
            try:
                r = radar.collect_radar(mode="search", keyword=k["keyword"], platform=k["platform"], limit=6)
                print(f"[tick] 雷达 {k['platform']}:{k['keyword']} → {r}")
            except Exception as e:  # noqa: BLE001
                print(f"[tick] 雷达 {k['platform']}:{k['keyword']} 失败:{e}")
            db.conn().execute(
                "UPDATE radar_keywords SET last_run_at=? WHERE id=?",
                (db.now_iso(), k["id"]),
            )
        db.conn().commit()
        try:
            from . import brief

            brief.build_brief()  # 对标数据变了,简报态势同步刷新
        except Exception:  # noqa: BLE001
            pass
        _mark_next("radar_bench", 10080)

    # 告警:failing → 本地标记 + 推送(每日一次去重);恢复清理标记
    from . import notify as _notify

    failing = db.conn().execute(
        "SELECT id, last_error FROM sources WHERE health='failing'"
    ).fetchall()
    flag = ROOT / "data" / "alert.flag"
    if failing:
        detail = "\n".join(f"{r['id']}: {(r['last_error'] or '')[:80]}" for r in failing)
        try:
            flag.write_text(detail, encoding="utf-8")
        except OSError:
            pass
        print(f"[tick] 告警:{len(failing)} 个源 failing")
        if _notify.configured():
            _notify.maybe_notify_once_per_day("VidInsight 告警", f"{len(failing)} 个采集源失败:\n{detail}")
        else:
            print("[tick] 通知未配置(.env 加 SERVERCHAN_KEY 或 FEISHU_WEBHOOK 即推送)")
    elif flag.exists():
        flag.unlink()
        print("[tick] 全部恢复,告警标记已清除")


if __name__ == "__main__":
    tick()
