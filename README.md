## Vision AI 批量处理工具

一个基于视觉大模型的智能文档处理平台，支持 PDF OCR、图片识别与标注、批量处理与历史记录管理，自动输出 Markdown（.md）。

## ✨ 核心功能与作用

- **双模型支持**：本地 MLX 模型 与 云端 API 调用二选一，灵活部署
- **PDF 专项提取**：针对 PDF 的高质量文本结构化抽取，保持排版与分页
- **智能内容过滤**：自动清理 <think> 思考段、系统噪声，产出更纯净
- **历史记录与回溯**：记录处理项，快速打开生成的 Markdown 与原始文件
- **现代化 WebUI**：折叠式配置面板与进度反馈，界面简洁高效
- **容器化交付**：提供 Dockerfile 与 docker-compose，一键启动即用

---

## 🐳 Docker 部署（推荐）

```bash
# 1) 克隆项目
git clone <项目地址>
cd vision-ai-webui

# 2) 启动服务
docker-compose up -d

# 3) 访问应用
# 浏览器打开：http://localhost:8000
```

查看状态与日志：

```bash
docker-compose ps
docker-compose logs -f
docker-compose down
```

详细说明见：`Docker使用指南.md`

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

## 参考与文档

- 详细使用说明请见：`综合使用指南.md`
- Docker 详细说明请见：`Docker使用指南.md`
