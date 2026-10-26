"""配置:路径与常量(中台根目录相对定位,零环境变量依赖)"""
from pathlib import Path

# 项目根 = backend/ 的上一级
ROOT = Path(__file__).resolve().parent.parent

# 统一数据库
PLATFORM_DB = ROOT / "data" / "platform.db"

# douyin-mcp(外部采集源,vendors 隔离)
DOUYIN_MCP_DIR = ROOT / "vendors" / "douyin-mcp"
DOUYIN_MCP_VENV = DOUYIN_MCP_DIR / ".venv" / "Scripts"
DOUYIN_MCP_DB = DOUYIN_MCP_DIR / "data" / "douyin.sqlite"
DOUYIN_MCP_PY = DOUYIN_MCP_VENV / "python.exe"

# API
API_HOST = "127.0.0.1"
API_PORT = 8787

# 调度(分钟):douyin 自数据每日一次,足够且安全
SOURCE_INTERVALS = {"douyin_self": 24 * 60}

# 对标雷达默认关键词(每周自动扫一轮;可用环境变量 RADAR_KEYWORDS_BILI/RADAR_KEYWORDS_YT 覆盖,逗号分隔)
import os

RADAR_KEYWORDS = {
    "bilibili": [
        w.strip() for w in os.getenv("RADAR_KEYWORDS_BILI", "哲学 思辨,斯多葛主义,存在主义,尼采").split(",") if w.strip()
    ],
    "youtube": [
        w.strip() for w in os.getenv("RADAR_KEYWORDS_YT", "stoicism,philosophy of life,meaning of life").split(",") if w.strip()
    ],
}

BJ_TZ = "Asia/Shanghai"
