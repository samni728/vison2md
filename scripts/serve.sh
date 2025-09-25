#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# 固定端口配置
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

# 检查端口是否被占用
is_port_busy() {
  lsof -i tcp:"$1" >/dev/null 2>&1
}

if is_port_busy "$PORT"; then
  echo "❌ 端口 $PORT 已被占用！"
  echo "请选择以下解决方案："
  echo "1. 停止占用端口的进程"
  echo "2. 设置环境变量使用其他端口: PORT=8001 ./scripts/serve.sh"
  echo "3. 手动杀死占用进程: lsof -ti:$PORT | xargs kill -9"
  echo ""
  echo "当前占用端口的进程："
  lsof -i tcp:"$PORT" 2>/dev/null || echo "无法获取进程信息"
  exit 1
fi

echo "🚀 启动 Qwen2.5-VL WebUI 服务器"
echo "📍 地址: http://$HOST:$PORT"
echo "⏹️  按 Ctrl+C 停止服务器"

# 同步依赖（如已安装会快速跳过）
if command -v uv >/dev/null 2>&1; then
  uv sync
else
  echo "未检测到 uv，请先安装 uv: https://astral.sh/uv" >&2
  exit 1
fi

# 启动服务
exec uv run uvicorn server.main:app --host "$HOST" --port "$PORT" --reload
