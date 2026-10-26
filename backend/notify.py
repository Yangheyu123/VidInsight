"""通知通道:Server酱(微信)/ 飞书 webhook 双适配,环境变量驱动

.env 配置(二选一或都配,都配则双发):
  SERVERCHAN_KEY=xxx        Server酱 SendKey
  FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hooks/xxx
未配置 → 静默跳过(不报错,不影响主流程)。
"""
import json
import os
import urllib.request

from .config import ROOT


def send(title: str, text: str) -> bool:
    """推送一条通知;任一通道成功即 True"""
    ok = False
    key = os.getenv("SERVERCHAN_KEY", "").strip()
    if key:
        try:
            req = urllib.request.Request(
                f"https://sctapi.ftqq.com/{key}.send",
                data=f"title={title}&desp={text}".encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            urllib.request.urlopen(req, timeout=10)
            ok = True
        except Exception:  # noqa: BLE001
            pass
    hook = os.getenv("FEISHU_WEBHOOK", "").strip()
    if hook:
        try:
            req = urllib.request.Request(
                hook,
                data=json.dumps({"msg_type": "text", "content": {"text": f"{title}\n{text}"}}).encode(),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=10)
            ok = True
        except Exception:  # noqa: BLE001
            pass
    return ok


def configured() -> bool:
    return bool(os.getenv("SERVERCHAN_KEY", "").strip() or os.getenv("FEISHU_WEBHOOK", "").strip())


def maybe_notify_once_per_day(title: str, text: str) -> None:
    """同一天只发一次(告警去重;恢复由调用方清理标记)"""
    flag = ROOT / "data" / "notify_last.date"
    today = __import__("datetime").date.today().isoformat()
    try:
        if flag.exists() and flag.read_text(encoding="utf-8").strip() == today:
            return
        if send(title, text):
            flag.parent.mkdir(parents=True, exist_ok=True)
            flag.write_text(today, encoding="utf-8")
    except OSError:
        pass
