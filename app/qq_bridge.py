from __future__ import annotations

import logging
from pathlib import Path
import re
import threading
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import AppConfig, load_config
from app.services.ai_grader import AIGrader, GradeResult
from app.services.excel_writer import ExcelWriterService, build_record
from app.utils.helpers import setup_logger


logger = logging.getLogger(__name__)


def _join_items(items: list[str]) -> str:
    return "；".join(items)


def _format_grade_for_qq(result: GradeResult, saved_path: Path | None = None) -> str:
    dimensions = "\n".join(f"{key}: {value}" for key, value in result.dimension_scores.items()) or "无"
    strengths = _join_items(result.strengths) or "无"
    weaknesses = _join_items(result.weaknesses) or "无"
    suggestions = _join_items(result.suggestions) or "无"
    knowledge_points = _join_items(result.knowledge_points) or "无"
    saved_line = f"\n已保存: {saved_path}" if saved_path else ""

    return (
        "【大模型作业批改结果】\n"
        f"姓名: {result.name}\n"
        f"学号: {result.student_id}\n"
        f"题目: {result.title}\n"
        f"总分: {result.score}/100\n"
        f"等级: {result.level}\n"
        f"维度评分:\n{dimensions}\n"
        f"优点: {strengths}\n"
        f"不足: {weaknesses}\n"
        f"改进建议: {suggestions}\n"
        f"知识点: {knowledge_points}\n"
        f"学术风险: {result.academic_risk}\n"
        f"总评: {result.comment}"
        f"{saved_line}"
    )


class QQBridge:
    """OneBot/NapCat HTTP 回调桥接。"""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.grader = AIGrader(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
            model=config.qq_openai_model,
            temperature=config.temperature,
        )
        self.excel_writer = ExcelWriterService(config.excel_file)
        self._excel_lock = threading.Lock()

    def extract_message(self, payload: dict[str, Any]) -> str:
        message = payload.get("raw_message") or payload.get("message") or ""
        if isinstance(message, list):
            text_parts = []
            for segment in message:
                if isinstance(segment, dict) and segment.get("type") == "text":
                    text_parts.append(str(segment.get("data", {}).get("text", "")))
            message_text = "".join(text_parts)
        else:
            message_text = str(message)
        message_text = re.sub(r"^\s*(?:\[CQ:at,[^\]]+\]\s*)+", "", message_text)
        return message_text.strip()

    def extract_command_body(self, text: str) -> str | None:
        candidates = [
            self.config.qq_command_prefix,
            "#批改",
            "批改",
            "/批改",
            "!批改",
            "#grade",
            "/grade",
        ]
        normalized = text.strip()
        for prefix in candidates:
            if normalized.startswith(prefix):
                return normalized[len(prefix):].strip()
        return None

    def save_result(self, payload: dict[str, Any], result: GradeResult) -> Path:
        dimensions = result.dimension_scores
        message_id = str(payload.get("message_id", ""))
        user_id = str(payload.get("user_id", ""))
        group_id = str(payload.get("group_id", ""))
        file_name = f"QQ文本消息-{message_id or user_id or 'unknown'}"

        record = build_record(file_name, {
            "来源": "QQ",
            "QQ用户": user_id,
            "QQ群": group_id,
            "消息ID": message_id,
            "姓名": result.name,
            "学号": result.student_id,
            "作业题目": result.title,
            "评分": result.score,
            "等级": result.level,
            "内容完整性": dimensions.get("内容完整性", 0),
            "技术理解": dimensions.get("技术理解", 0),
            "实践过程": dimensions.get("实践过程", 0),
            "创新应用": dimensions.get("创新应用", 0),
            "表达规范": dimensions.get("表达规范", 0),
            "评语": result.comment,
            "优点": _join_items(result.strengths),
            "不足": _join_items(result.weaknesses),
            "改进建议": _join_items(result.suggestions),
            "知识点": _join_items(result.knowledge_points),
            "学术风险": result.academic_risk,
        })
        with self._excel_lock:
            return self.excel_writer.append_rows([record])

    def build_reply(self, payload: dict[str, Any]) -> str | None:
        text = self.extract_message(payload)
        homework = self.extract_command_body(text)
        if homework is None:
            return None

        if not homework:
            return (
                f"请按格式发送: {self.config.qq_command_prefix} 姓名、学号、题目和作业正文。\n"
                "如果作业是 docx/pdf/txt 文件，请先用网页端上传批改。"
            )

        if len(homework) > self.config.qq_max_chars:
            homework = homework[: self.config.qq_max_chars]

        result = self.grader.grade_content(homework)
        saved_path = self.save_result(payload, result)
        logger.info("QQ 批改结果已保存: %s", saved_path)
        return _format_grade_for_qq(result, saved_path)


def build_qq_app(config: AppConfig) -> FastAPI:
    bridge = QQBridge(config)
    app = FastAPI(title="大模型作业批改 QQ 桥接服务")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/qq/webhook")
    async def onebot_webhook(request: Request) -> JSONResponse:
        payload = await request.json()
        try:
            reply = bridge.build_reply(payload)
        except Exception as exc:  # noqa: BLE001
            logger.exception("QQ 批改失败")
            raise HTTPException(status_code=500, detail=f"批改失败: {exc}") from exc

        if reply is None:
            return JSONResponse({"reply": ""})
        return JSONResponse({"reply": reply, "message": reply})

    return app


def main() -> None:
    import uvicorn

    config = load_config()
    setup_logger(config.log_level)
    uvicorn.run(
        build_qq_app(config),
        host=config.qq_bridge_host,
        port=config.qq_bridge_port,
    )


if __name__ == "__main__":
    main()
