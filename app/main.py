from __future__ import annotations

import logging
import os
from typing import Iterator

import gradio as gr

from app.config import AppConfig, load_config
from app.file_reader import normalize_uploaded_files, read_file_content
from app.services.ai_grader import AIGrader
from app.services.excel_writer import ExcelWriterService, build_record
from app.utils.helpers import ensure_directory, get_local_ip, setup_logger


logger = logging.getLogger(__name__)


def _join_items(items: list[str]) -> str:
    return "；".join(items)


class HomeworkApp:
    """作业批改主流程。"""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        ensure_directory(config.upload_dir)
        self.grader = AIGrader(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
            model=config.openai_model,
            temperature=config.temperature,
        )
        self.excel_writer = ExcelWriterService(config.excel_file)

    def process_batch(self, files: list[object] | None) -> Iterator[tuple[str, str]]:
        paths = normalize_uploaded_files(files)
        if not paths:
            yield "### 等待开始\n\n请先上传文件。", "未上传文件"
            return

        total = len(paths)
        success = 0
        buffer_rows: list[dict[str, object]] = []
        content_md = f"# 开始批改\n\n共接收 **{total}** 个文件。\n\n---\n\n"

        for index, path in enumerate(paths, start=1):
            logger.info("开始处理文件: %s", path)
            content_md += f"## 处理文件 ({index}/{total}): {path.name}\n\n"
            yield content_md, f"正在读取: {path.name}"

            read_result = read_file_content(path)
            if read_result.error:
                logger.warning("读取失败: %s, 原因: %s", path, read_result.error)
                content_md += f"**读取失败**: {read_result.error}\n\n---\n\n"
                yield content_md, f"读取失败: {path.name}"
                continue

            content_md += "正在分析作业内容...\n\nAI 正在生成评语...\n\n**评语内容:**\n\n"
            yield content_md, f"AI 批改中: {path.name}"

            raw_text = ""
            try:
                for chunk in self.grader.stream_grade(read_result.content):
                    raw_text += chunk
                    content_md += chunk
                    yield content_md, f"AI 生成中... ({len(raw_text)} 字符)"

                parsed = self.grader.parse_grade_response(raw_text)
                content_md += (
                    "\n\n---\n\n"
                    f"## 批改完成\n\n"
                    f"- 姓名: {parsed.name}\n"
                    f"- 学号: {parsed.student_id}\n"
                    f"- 作业题目: {parsed.title}\n"
                    f"- 评分: {parsed.score}/100\n"
                    f"- 等级: {parsed.level}\n"
                    f"- 维度评分: {parsed.dimension_scores}\n"
                    f"- 评语: {parsed.comment}\n"
                    f"- 优点: {_join_items(parsed.strengths)}\n"
                    f"- 不足: {_join_items(parsed.weaknesses)}\n"
                    f"- 改进建议: {_join_items(parsed.suggestions)}\n"
                    f"- 知识点: {_join_items(parsed.knowledge_points)}\n"
                    f"- 学术风险: {parsed.academic_risk}\n"
                )
                dimensions = parsed.dimension_scores
                buffer_rows.append(build_record(path.name, {
                    "姓名": parsed.name,
                    "学号": parsed.student_id,
                    "作业题目": parsed.title,
                    "评分": parsed.score,
                    "等级": parsed.level,
                    "内容完整性": dimensions.get("内容完整性", 0),
                    "技术理解": dimensions.get("技术理解", 0),
                    "实践过程": dimensions.get("实践过程", 0),
                    "创新应用": dimensions.get("创新应用", 0),
                    "表达规范": dimensions.get("表达规范", 0),
                    "评语": parsed.comment,
                    "优点": _join_items(parsed.strengths),
                    "不足": _join_items(parsed.weaknesses),
                    "改进建议": _join_items(parsed.suggestions),
                    "知识点": _join_items(parsed.knowledge_points),
                    "学术风险": parsed.academic_risk,
                }))
                success += 1
                yield content_md, f"批改完成: {path.name}"
            except Exception as exc:  # noqa: BLE001
                logger.exception("AI 批改失败: %s", path)
                content_md += f"\n\n**AI 批改失败**: {exc}\n\n---\n\n"
                yield content_md, f"批改失败: {path.name}"

        try:
            saved_path = self.excel_writer.append_rows(buffer_rows)
            content_md += (
                "\n## 汇总\n\n"
                f"- 成功批改: {success} 个\n"
                f"- 失败: {total - success} 个\n"
                f"- Excel 记录: {saved_path}\n"
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Excel 保存失败")
            content_md += f"\n## 保存失败\n\n{exc}\n"

        yield content_md, f"完成: {success}/{total}"


def build_interface(config: AppConfig) -> gr.Blocks:
    app = HomeworkApp(config)
    local_ip = get_local_ip()

    with gr.Blocks(theme=gr.themes.Soft(primary_hue="orange"), title="作业批改系统") as demo:
        gr.Markdown("## 大模型课程作业智能批改系统")
        gr.Markdown("支持多文件上传、流式批改、多维评分、知识点识别、学术风险提示和 Excel 留档。")
        gr.Markdown(
            f"""
### 访问方式
- 本地访问: http://127.0.0.1:{config.gradio_port}
- 局域网访问: http://{local_ip}:{config.gradio_port}
"""
        )

        with gr.Row():
            with gr.Column(scale=1):
                file_input = gr.Files(label="上传作业文件（可多选）", file_types=[".txt", ".docx", ".pdf"])
                submit_btn = gr.Button("开始批量批改", variant="primary")
                clear_btn = gr.Button("清空结果", variant="secondary")
            with gr.Column(scale=2):
                log_output = gr.Markdown(value="### 等待开始\n\n请先上传文件。", height=500)
                status_output = gr.Textbox(label="当前状态", value="就绪", interactive=False)

        submit_btn.click(fn=app.process_batch, inputs=file_input, outputs=[log_output, status_output])
        clear_btn.click(fn=lambda: ("### 等待开始\n\n请先上传文件。", "就绪"), outputs=[log_output, status_output])

    return demo


def main() -> None:
    config = load_config()
    os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1,::1")
    os.environ.setdefault("no_proxy", "localhost,127.0.0.1,::1")
    setup_logger(config.log_level)
    logger.info("服务启动中")
    logger.info("Excel 记录文件: %s", config.excel_file)
    logger.info("上传目录: %s", config.upload_dir)
    logger.info("公网映射: %s", "启用" if config.enable_ngrok else "禁用")

    demo = build_interface(config)
    launch_kwargs = dict(server_name=config.gradio_host, server_port=config.gradio_port, quiet=False)
    if config.enable_ngrok:
        try:
            from pyngrok import ngrok

            if config.ngrok_authtoken:
                ngrok.set_auth_token(config.ngrok_authtoken)
            public_url = ngrok.connect(config.gradio_port)
            logger.info("公网地址: %s", public_url.public_url)
        except Exception as exc:  # noqa: BLE001
            logger.exception("ngrok 启动失败")
            logger.warning("将仅提供局域网访问: %s", exc)

    demo.launch(**launch_kwargs)
