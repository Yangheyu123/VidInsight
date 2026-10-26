"""ASR 引擎:faster-whisper 本地转写(模型懒加载,进程内复用)

模型:环境变量 ASR_MODEL,默认 small(中文效果/速度均衡;base 更快更糙)
下载走 hf-mirror(国内加速);首次使用自动下载,之后走本地缓存。
原则:只留文字,音频文件由调用方用完即删。
"""
import os

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# ---- av 19 兼容补丁:faster-whisper 1.2.1 的 decode_audio 仍传已移除的
# metadata_errors 参数;剥离之(只影响本进程,行为等价) ----
try:
    import av as _av

    _av_open_orig = _av.open

    def _av_open_compat(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _av_open_orig(*args, **kwargs)

    _av.open = _av_open_compat
except ImportError:  # av 未装时由 faster-whisper 依赖带入,这里不提前失败
    pass

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        name = os.getenv("ASR_MODEL", "small")
        # CPU int8:无 GPU 依赖,速度可接受(短视频 1-3 分钟音频约 30-90 秒)
        _model = WhisperModel(name, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str, lang: str = "zh") -> str:
    """音频文件 → 纯文本(合并分段;失败抛异常由上层跳过)"""
    segments, _info = _get_model().transcribe(
        audio_path,
        language=lang,
        vad_filter=True,
        beam_size=5,
        condition_on_previous_text=False,
    )
    return "".join(seg.text.strip() for seg in segments).strip()
