## Vision AI 批量处理工具

一个基于视觉大模型的智能文档处理平台，支持 PDF OCR、图片识别与标注、批量处理与历史记录管理，自动输出 Markdown（.md）。

## ✨ 核心功能与作用

- **双模型支持**：本地 MLX 模型 与 云端 API 调用二选一，灵活部署
- **PDF 专项提取**：针对 PDF 的高质量文本结构化抽取，保持排版与分页
- **智能内容过滤**：自动清理 <think> 思考段、系统噪声，产出更纯净
- **历史记录与回溯**：记录处理项，快速打开生成的 Markdown 与原始文件
- **现代化 WebUI**：折叠式配置面板与进度反馈，界面简洁高效
- **容器化交付**：提供**API-only**和**完整模式**两种 Docker 部署方案
- **MCP 集成能力**：为 LLM 提供**视觉多模态调用**功能

---

## 🐳 Docker 部署（推荐）

### 🚀 API-only 模式（轻量级，推荐用于 API 调用）

> **适用场景**：服务器快速部署、k8s 集群、只调用 API 处理的场景

**优势**：

- ⚡ 构建速度快（跳过 MLX/torch 等依赖）
- 📦 镜像体积小（约为完整模式的 1/3）
- 🎯 资源消耗低，适合服务器部署

```bash
# 1) 克隆项目
git clone <项目地址>
cd vision-ai-webui

# 2) 使用 API-only 模式启动（轻量级，镜像体积小）
export DOCKERFILE=Dockerfile.api
docker-compose build && docker-compose up -d

# 或者使用快速部署脚本
./快速部署.sh

# 3) 访问应用
# 浏览器打开：http://localhost:8000
```

### 🎯 完整模式（包含本地推理功能）

> **适用场景**：本地高性能处理、离线环境、无网络依赖的需求

**优势**：

- 🔥 本地推理能力强，无网络瓶颈
- 🏠 适合内网/离线环境
- 💪 处理性能更优秀，延迟更低

```bash
# 1) 克隆项目
git clone <项目地址>
cd vision-ai-webui

# 2) 启动完整服务
docker-compose up -d

# 3) 访问应用
# 浏览器打开：http://localhost:8000
```

#### 🎛️ 管理命令

```bash
# 查看状态与日志
docker-compose ps
docker-compose logs -f
docker-compose down

# API-only模式一键重新部署
DOCKERFILE=Dockerfile.api docker-compose up -d --build
```

详细说明见：`Docker使用指南.md`

#### 📊 快速决策指南

| 使用场景             | 推荐模式     | 命令示例                                                |
| -------------------- | ------------ | ------------------------------------------------------- |
| 🖥️ 服务端快速部署    | **API-only** | `DOCKERFILE=Dockerfile.api docker-compose up -d`        |
| 📱 生产环境 API 服务 | **API-only** | `./快速部署.sh`                                         |
| 💻 本地开发调试      | **完整模式** | `docker-compose up`                                     |
| 🔒 内网/离线处理     | **完整模式** | `docker-compose up -d`                                  |
| ☁️ 云主机/K8S 部署   | **API-only** | `export DOCKERFILE=Dockerfile.api && docker-compose up` |

---

## 本地开发（uv 环境）

```bash
# 安装 uv（如未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖（读取 pyproject.toml）
uv sync

# 启动服务（端口 8000）
uv run uvicorn server.main:app --host 127.0.0.1 --port 8000 --reload
```

一键脚本：

```bash
chmod +x scripts/serve.sh
./scripts/serve.sh
# 固定端口为 8000（如需更改，请自行修改脚本或命令）
```

---

## 界面与使用要点

- **折叠面板顺序**：`模型配置` → `配置管理` → `提示词类型`（默认折叠）
- **上传与处理**：拖放 PDF/图片 → 选择提示词 → 点击开始 → 实时进度
- **结果预览**：每个任务生成 `.md`，并保留到 `outputs/`（仓库已忽略）
- **原始文件链接**：生成的 `.md` 内包含指向 `/uploads/...` 的相对链接，浏览器按当前访问地址解析，适配不同反向代理/端口
- **历史记录**：在“历史记录”区域查看过往任务，支持打开 Markdown/原始文件与删除记录

---

## 常用 API（节选）

- `POST /api/process`：上传并处理文件（多文件，表单字段：`files`、`prompt`、`model_path`、`max_tokens`、`temperature` 等）
- `GET /api/history`：获取历史记录（含生成的 `.md` 与原始文件链接）
- `DELETE /api/history?record_id=...`：删除某条历史记录

---

## 目录与版本控制约定

- `uploads/` 与 `outputs/` 仅用于运行时文件，已加入 `.gitignore`，不会推送到远程仓库
- 请勿将本地虚拟环境（如 `.venv/`）提交到仓库

---

## 🤖 MCP 集成（LLM 多模态支持）

项目现已支持 **MCP（Model Context Protocol）** 集成，让普通的文本 LLM 获得强大的视觉处理能力。

### 🔧 MCP 工具

| 工具名称                  | 功能描述          | 使用场景                 |
| ------------------------- | ----------------- | ------------------------ |
| `document_ocr`            | PDF 文档 OCR 识别 | 文档转文本，保持格式     |
| `analyze_image`           | 图片内容分析      | 视觉描述，内容识别       |
| `extract_structured_data` | 结构化数据提取    | 发票、表单、合同信息提取 |
| `batch_process_documents` | 批量文档处理      | 多文档统一处理           |

### 🚀 LLM 集成示例

```bash
# 安装MCP依赖
pip install mcp

# 启动MCP服务器
python server/mcp_server.py
```

**使普通 LLM 获得多模态功能**：

- 📄 **PDF 识别** → LLM 可以分析 PDF 内容
- 🙌 **图片理解** → LLM 可以描述图片内容
- 📋 **智能提取** → LLM 可以处理结构化数据
- 🔄 **批量处理** → LLM 可以管理多个文档

---

## 参考与文档

- 详细使用说明请见：`综合使用指南.md`
- Docker 详细说明请见：`Docker使用指南.md`
- MCP 多模态集成：`MCP使用指南.md`
