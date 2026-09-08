from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Optional

from dotenv import load_dotenv


@dataclass(slots=True)
class AppConfig:
    """应用配置。"""

    openai_api_key: str
    openai_base_url: str
    openai_model: str
    excel_file: Path
    upload_dir: Path
    log_level: str
    gradio_host: str
    gradio_port: int
    enable_ngrok: bool
    ngrok_authtoken: str
    temperature: float
    max_file_size_mb: int
    enable_qq_bridge: bool
    qq_bridge_host: str
    qq_bridge_port: int
    qq_command_prefix: str
    qq_openai_model: str
    qq_max_chars: int


def _get_env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise ValueError(f"缺少必要环境变量: {name}")
    return value


def _get_bool(name: str, default: str = "false") -> bool:
    return _get_env(name, default).lower() in {"1", "true", "yes", "on"}


def load_config() -> AppConfig:
    """从 .env 加载运行配置。"""

    load_dotenv(override=False)
    base_dir = Path(__file__).resolve().parents[2]

    return AppConfig(
        openai_api_key=_get_env("OPENAI_API_KEY"),
        openai_base_url=_get_env("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        openai_model=_get_env("OPENAI_MODEL", "qwen-plus"),
        excel_file=(base_dir / _get_env("EXCEL_FILE", "作业批改记录.xlsx")).resolve(),
        upload_dir=(base_dir / _get_env("UPLOAD_DIR", "uploads")).resolve(),
        log_level=_get_env("LOG_LEVEL", "INFO"),
        gradio_host=_get_env("GRADIO_HOST", "0.0.0.0"),
        gradio_port=int(_get_env("GRADIO_PORT", "7861")),
        enable_ngrok=_get_bool("ENABLE_NGROK", "false"),
        ngrok_authtoken=os.getenv("NGROK_AUTHTOKEN", ""),
        temperature=float(_get_env("TEMPERATURE", "0.3")),
        max_file_size_mb=int(_get_env("MAX_FILE_SIZE_MB", "20")),
        enable_qq_bridge=_get_bool("ENABLE_QQ_BRIDGE", "false"),
        qq_bridge_host=_get_env("QQ_BRIDGE_HOST", "0.0.0.0"),
        qq_bridge_port=int(_get_env("QQ_BRIDGE_PORT", "8088")),
        qq_command_prefix=_get_env("QQ_COMMAND_PREFIX", "#批改"),
        qq_openai_model=_get_env("QQ_OPENAI_MODEL", "qwen-turbo"),
        qq_max_chars=int(_get_env("QQ_MAX_CHARS", "2500")),
    )
