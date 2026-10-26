"""LLM 客户端(OpenAI 兼容协议)

默认指向 BigModel(智谱)Coding Plan 的 GLM-5.3-Flash(订阅内调用,走 coding 专用端点):
  LLM_API_KEY   必填(BigModel API Key)——放在项目根 .env 一行即可
  LLM_BASE_URL  默认 https://open.bigmodel.cn/api/coding/paas/v4
  LLM_MODEL     默认 glm-5.3-flash
未配置 Key 时所有 AI 功能走规则降级,不报错。
注意:GLM 思考型模型会消耗思考 token,max_tokens 需给足(本模块统一 4096)。
"""
import os

from .config import ROOT

_FLAG = ROOT / "data" / ".llm_unavailable"  # 降级标记(连续失败后本进程内熔断)


def _load_dotenv() -> None:
    """极简 .env 加载(不引入依赖):KEY=VALUE 每行一条,# 注释"""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except OSError:
        pass


_load_dotenv()


def get_client():
    """返回 OpenAI 客户端;未配置 Key 或已熔断 → None(调用方走降级)"""
    if _FLAG.exists():
        return None
    key = os.getenv("LLM_API_KEY", "").strip()
    if not key:
        return None
    from openai import OpenAI

    return OpenAI(
        api_key=key,
        base_url=os.getenv("LLM_BASE_URL", "").strip() or "https://open.bigmodel.cn/api/coding/paas/v4",
        timeout=600,  # GLM 思考型:配合流式,600s 上限
    )


def model_name() -> str:
    return os.getenv("LLM_MODEL", "").strip() or "glm-5.3-flash"


def chat(system: str, user: str, temperature: float = 0.4) -> str | None:
    """同步对话;任何失败(网络/鉴权/超时)→ 打熔断标记并返回 None"""
    client = get_client()
    if client is None:
        return None
def _call(client, system: str, user: str, temperature: float, max_tokens: int, disable_thinking: bool):
    """流式调用(思考型模型长时间推理也不会触发整请求超时);
    disable_thinking=True 时关闭思考(额度全部给正文)"""
    kwargs = {}
    if disable_thinking:
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    stream = client.chat.completions.create(
        model=model_name(),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        **kwargs,
    )
    parts: list[str] = []
    for chunk in stream:
        try:
            delta = chunk.choices[0].delta.content
        except (IndexError, AttributeError):
            delta = None
        if delta:
            parts.append(delta)
    return "".join(parts).strip()


def chat(system: str, user: str, temperature: float = 0.4, max_tokens: int = 16384) -> str | None:
    """同步对话;正文为空(思考耗尽额度)时关思考重试一次;异常→熔断降级"""
    client = get_client()
    if client is None:
        return None
    try:
        content = _call(client, system, user, temperature, max_tokens, disable_thinking=False)
        if content:
            return content
        return _call(client, system, user, temperature, max_tokens, disable_thinking=True) or None
    except Exception:  # noqa: BLE001 - LLM 不可用一律降级
        try:
            _FLAG.write_text("llm unavailable", encoding="utf-8")
        except OSError:
            pass
        return None


def llm_configured() -> bool:
    return bool(os.getenv("LLM_API_KEY", "").strip()) and not _FLAG.exists()
