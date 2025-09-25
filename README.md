# Vision AI 批量处理工具

一个基于视觉大模型的智能文档处理平台，支持 PDF OCR、图片识别、文档打标签等批量处理功能。可批量拖放 PDF/图片，调用视觉模型识别并保存为 Markdown（.md）。

## 依赖

- macOS（Apple Silicon 建议）
- Python 3.10 - 3.12
- 已可在终端运行：
  ```bash
  python -m mlx_vlm.generate --help
  ```

## 🐳 Docker 部署（推荐）

### 快速启动

```bash
# 1) 克隆项目
git clone <项目地址>
cd vision-ai-webui

# 2) 启动服务
docker-compose up -d

# 3) 访问应用
# 浏览器打开：http://localhost:8000
```

### 查看状态和日志

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

详细的 Docker 使用说明请参考：[Docker 使用指南.md](./Docker使用指南.md)

## 使用 uv 管理环境（本地开发）

```bash
cd /Users/samni/Desktop/开发项目/qwen2.5vl_webui
# 1) 安装 uv（如未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh
# 2) 安装依赖（读取 pyproject.toml）
uv sync
# 3) 启动服务（8001 端口）
uv run uvicorn server.main:app --host 127.0.0.1 --port 8001 --reload
```

打开浏览器访问：http://127.0.0.1:8001

## 一键启动脚本（自动找空闲端口）

```bash
# 赋予执行权限
chmod +x scripts/serve.sh
# 启动（默认 8001，若被占用会自动往上递增）
./scripts/serve.sh
# 或自定义端口
PORT=8010 ./scripts/serve.sh
```

启动后终端会显示监听端口，浏览器打开对应地址即可访问 WebUI。

## 界面使用

1. 填写模型路径（默认：`/Users/samni/.cache/lm-studio/models/EZCon/Qwen2.5-VL-7B-Instruct-4bit-mlx`）、提示词、max_tokens、temperature。
2. 拖放 PDF 或图片（支持多选）到投递区，点击“开始识别”。
3. 结果区显示保存的 Markdown 链接；文件保存在 `outputs/`。

## 接口

- `POST /api/process`
  - 表单字段：`files`(多文件)、`prompt`、`model_path`、`max_tokens`、`temperature`
  - 返回：各个文件对应的 `.md` 输出路径
