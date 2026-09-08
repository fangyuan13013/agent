from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Iterator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


SYSTEM_PROMPT = """
你是一个面向高校课程的大模型作业批改智能体。请根据学生提交的作业内容，完成以下任务：
1. 提取：姓名、学号、作业题目。
2. 从课程目标、内容完整性、技术理解、实践过程、表达规范五个维度评分。
3. 生成有依据的总评、优点、不足、改进建议和疑似学术风险提示。
4. 如果作业内容与“大模型、提示词工程、RAG、智能体、模型部署、模型评测、AI应用开发”等主题相关，请重点评价技术路线、实验过程、工程落地和反思深度。

请严格按如下 JSON 格式输出，不要包含 Markdown 代码块标记：
{
  "姓名": "提取到的姓名",
  "学号": "提取到的学号",
  "作业题目": "提取到的题目",
  "评分": 85,
  "等级": "良好",
  "维度评分": {
    "内容完整性": 18,
    "技术理解": 22,
    "实践过程": 20,
    "创新应用": 12,
    "表达规范": 13
  },
  "评语": "这里是具体的评分理由...",
  "优点": ["优点1", "优点2"],
  "不足": ["不足1", "不足2"],
  "改进建议": ["建议1", "建议2"],
  "知识点": ["大模型", "提示词工程"],
  "学术风险": "未发现明显抄袭或 AI 代写风险"
}
""".strip()


@dataclass(slots=True)
class GradeResult:
    """单个文件的 AI 评分结果。"""

    raw_text: str
    name: str
    student_id: str
    title: str
    score: int
    level: str
    dimension_scores: dict[str, int]
    comment: str
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    knowledge_points: list[str]
    academic_risk: str


class AIGrader:
    """封装 AI 批改能力。"""

    def __init__(self, api_key: str, base_url: str, model: str, temperature: float) -> None:
        self._client = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            streaming=True,
        )

    def stream_grade(self, content: str) -> Iterator[str]:
        """流式输出 AI 返回内容。"""

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"作业内容如下：\n\n{content}"),
        ]
        for chunk in self._client.stream(messages):
            if getattr(chunk, "content", None):
                yield chunk.content

    def grade_content(self, content: str) -> "GradeResult":
        """非流式批改文本，供 QQ 机器人等接口复用。"""

        raw_text = "".join(self.stream_grade(content))
        return self.parse_grade_response(raw_text)

    @staticmethod
    def parse_grade_response(raw_text: str) -> GradeResult:
        """从模型输出中提取 JSON。"""

        def _coerce_int(value: object, default: int = 0) -> int:
            try:
                return int(float(str(value).strip()))
            except (TypeError, ValueError):
                return default

        def _string_list_from_text(name: str) -> list[str]:
            patterns = [
                rf"{name}\s*[:：]\s*(.+)",
                rf"{name}\s*-\s*(.+)",
            ]
            for pattern in patterns:
                match = re.search(pattern, raw_text)
                if match:
                    value = match.group(1).strip()
                    if value:
                        parts = re.split(r"[；;，,、\n]+", value)
                        return [part.strip() for part in parts if part.strip()]
            return []

        data: dict[str, object] = {}
        candidates = []
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.S | re.I)
        if fenced:
            candidates.append(fenced.group(1))
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start >= 0 and end > start:
            candidates.append(raw_text[start:end])
        for candidate in candidates:
            try:
                data = json.loads(candidate)
                break
            except json.JSONDecodeError:
                continue

        def _get_text(name: str, default: str = "未知") -> str:
            value = data.get(name)
            if isinstance(value, str) and value.strip():
                return value.strip()
            match = re.search(rf"{name}\s*[:：]\s*(.+)", raw_text)
            if match:
                return match.group(1).strip()
            return default

        def _string_list(name: str) -> list[str]:
            value = data.get(name, [])
            if isinstance(value, list):
                return [str(item).strip() for item in value if str(item).strip()]
            if isinstance(value, str) and value.strip():
                parts = re.split(r"[；;，,、\n]+", value)
                return [part.strip() for part in parts if part.strip()]
            return _string_list_from_text(name)

        dimension_scores = data.get("维度评分", {})
        if not isinstance(dimension_scores, dict):
            dimension_scores = {}

        parsed_dimensions: dict[str, int] = {}
        for key in ["内容完整性", "技术理解", "实践过程", "创新应用", "表达规范"]:
            parsed_dimensions[key] = _coerce_int(dimension_scores.get(key), 0)
            if parsed_dimensions[key] == 0:
                match = re.search(rf"{key}\s*[:：]\s*(\d+)", raw_text)
                if match:
                    parsed_dimensions[key] = _coerce_int(match.group(1), 0)

        return GradeResult(
            raw_text=raw_text,
            name=_get_text("姓名"),
            student_id=_get_text("学号"),
            title=_get_text("作业题目", _get_text("题目")),
            score=_coerce_int(data.get("评分", re.search(r"评分\s*[:：]\s*(\d+)", raw_text).group(1) if re.search(r"评分\s*[:：]\s*(\d+)", raw_text) else 0), 0),
            level=_get_text("等级", "未评级"),
            dimension_scores=parsed_dimensions,
            comment=_get_text("评语", raw_text.strip()[:500]),
            strengths=_string_list("优点"),
            weaknesses=_string_list("不足"),
            suggestions=_string_list("改进建议"),
            knowledge_points=_string_list("知识点"),
            academic_risk=_get_text("学术风险", "未提供"),
        )
