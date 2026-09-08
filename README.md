# 大模型课程作业智能批改系统

这是一个面向“大模型应用开发”课程的大作业项目。系统基于通义千问/OpenAI 兼容接口、LangChain、Gradio、FastAPI 和 Excel 数据留档，实现作业上传、文本解析、流式 AI 批改、多维评分、知识点识别、学术风险提示，以及 QQ/OneBot 机器人桥接能力。

## 项目特色

- 大模型批改：调用兼容 OpenAI 协议的大模型，对作业内容生成结构化评价。
- 多维评分：从内容完整性、技术理解、实践过程、创新应用、表达规范五个维度评分。
- 课程贴合：重点评价提示词工程、RAG、智能体、模型部署、模型评测、AI 应用开发等大模型主题。
- 流式输出：网页端实时显示模型生成过程，适合课堂演示。
- 多格式读取：支持 txt、docx、pdf 作业文件。
- Excel 留档：自动保存姓名、学号、题目、总分、等级、维度分、评语、优缺点和改进建议。
- 公网访问：可选使用 ngrok，把本地 Gradio 页面映射到公网。
- QQ 接入：提供 OneBot/NapCat HTTP 桥接服务，可在 QQ 中通过命令触发批改。

## 目录结构

```text
.
├── dazuoy.py
├── qqbot.py
├── .env.example
├── requirements.txt
└── app/
    ├── config.py
    ├── file_reader.py
    ├── main.py
    ├── qq_bridge.py
    ├── services/
    │   ├── ai_grader.py
    │   └── excel_writer.py
    └── utils/
        └── helpers.py
```

## 使用方法

1. 复制 `.env.example` 为 `.env`，填写 `OPENAI_API_KEY`。
2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 启动网页批改系统：

```bash
python dazuoy.py
```

启动后访问：

- 本机：`http://127.0.0.1:7861`
- 局域网：页面启动日志中会显示本机 IP 地址

## 环境变量

- `OPENAI_API_KEY`：必填，AI 接口密钥
- `OPENAI_BASE_URL`：模型服务地址
- `OPENAI_MODEL`：模型名称
- `EXCEL_FILE`：批改记录 Excel 文件名
- `UPLOAD_DIR`：上传文件缓存目录
- `GRADIO_HOST`：服务监听地址
- `GRADIO_PORT`：服务端口
- `ENABLE_NGROK`：是否启用公网映射
- `NGROK_AUTHTOKEN`：ngrok token
- `ENABLE_QQ_BRIDGE`：是否启用 QQ 桥接配置
- `QQ_BRIDGE_HOST`：QQ 桥接服务监听地址
- `QQ_BRIDGE_PORT`：QQ 桥接服务端口
- `QQ_COMMAND_PREFIX`：QQ 触发批改命令，默认 `#批改`

## QQ 部署方式

本项目不能直接登录 QQ 账号，需要配合 NapCat、Lagrange、go-cqhttp 兼容实现，使用 OneBot HTTP 回调接入。推荐使用 NapCat。

1. 安装并启动 NapCat，让 QQ 机器人账号在线。
2. 在 NapCat 的 HTTP 上报配置中添加上报地址：

```text
http://127.0.0.1:8088/qq/webhook
```

3. 启动作业批改 QQ 桥接服务：

```bash
python qqbot.py
```

4. 在 QQ 群或私聊里发送：

```text
#批改 姓名：张三
学号：20240001
题目：基于大模型的作业批改系统
正文：本文设计了一个基于提示词工程和 LangChain 的智能批改系统……
```

机器人会返回总分、等级、维度评分、优点、不足、改进建议、知识点和学术风险。docx/pdf/txt 文件仍建议通过网页端上传，因为 QQ 文件下载需要额外配置文件直链和权限。

## 大模型评分规则

| 维度 | 说明 |
| --- | --- |
| 内容完整性 | 是否包含课程要求的背景、目标、设计、实现和总结 |
| 技术理解 | 是否准确理解大模型、提示词、RAG、智能体、API 调用等概念 |
| 实践过程 | 是否体现真实开发、调试、测试和部署过程 |
| 创新应用 | 是否有较完整的场景设计、功能扩展或工程优化 |
| 表达规范 | 文档结构、语言表述、代码说明和结果展示是否清晰 |

## 说明

- 支持多文件批量批改。
- 支持流式输出 AI 评语。
- 支持 txt、docx、pdf 文件读取。
- 批改结果自动写入 Excel，便于教师留档和后续统计。
- QQ 桥接用于文本作业快速批改，网页端用于正式文件批改。
- 代码已拆分为配置、读取、AI 评分、Excel、QQ 桥接、工具和主程序模块。
