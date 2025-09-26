#!/bin/bash
# MCP服务器启动脚本

echo "启动Vision AI MCP服务器..."
echo "为LLM提供视觉处理和多模态能力"

# 设置Python路径
export PYTHONPATH=/app

# 确保目录存在
mkdir -p uploads outputs

# 启动MCP服务器
python -m server.mcp_server
