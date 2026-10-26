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

BJ_TZ = "Asia/Shanghai"
