from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd


@dataclass(slots=True)
class ExcelWriterService:
    """Excel 记录写入服务。"""

    excel_path: Path

    def append_rows(self, rows: list[dict[str, object]]) -> Path:
        """追加写入 Excel。"""

        if not rows:
            return self.excel_path

        new_df = pd.DataFrame(rows)
        if self.excel_path.exists():
            old_df = pd.read_excel(self.excel_path)
            final_df = pd.concat([old_df, new_df], ignore_index=True)
        else:
            final_df = new_df

        self.excel_path.parent.mkdir(parents=True, exist_ok=True)
        final_df.to_excel(self.excel_path, index=False)
        return self.excel_path


def build_record(file_name: str, result: dict[str, object]) -> dict[str, object]:
    """构造 Excel 记录行。"""

    return {
        "提交时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "来源": result.get("来源", "网页端"),
        "QQ用户": result.get("QQ用户", ""),
        "QQ群": result.get("QQ群", ""),
        "消息ID": result.get("消息ID", ""),
        "文件名": file_name,
        "姓名": result.get("姓名", "未知"),
        "学号": result.get("学号", "未知"),
        "题目": result.get("作业题目", "未知"),
        "评分": result.get("评分", 0),
        "等级": result.get("等级", "未评级"),
        "内容完整性": result.get("内容完整性", 0),
        "技术理解": result.get("技术理解", 0),
        "实践过程": result.get("实践过程", 0),
        "创新应用": result.get("创新应用", 0),
        "表达规范": result.get("表达规范", 0),
        "评语": result.get("评语", ""),
        "优点": result.get("优点", ""),
        "不足": result.get("不足", ""),
        "改进建议": result.get("改进建议", ""),
        "知识点": result.get("知识点", ""),
        "学术风险": result.get("学术风险", ""),
    }
