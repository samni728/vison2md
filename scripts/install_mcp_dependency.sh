#!/bin/bash
# MCP 依赖安装脚本

echo "🔧 安装 MCP 集成依赖..."

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "❌ Python 未安装，请先安装 Python"
    exit 1
fi

# 检查pip环境
if ! command -v pip &> /dev/null; then
    echo "❌ pip 未安装，请先安装 pip"
    exit 1
fi

echo "📦 安装 MCP 库..."
pip install mcp

if [ $? -eq 0 ]; then
    echo "✅ MCP 库安装成功！"
    echo ""
    echo "🎯 下一步操作："
    echo "1. 启动服务: python server/mcp_server.py"
    echo "2. 配置您的 LLM 客户端以使用 MCP 服务"
    echo "3. 测试工具调用"
else
    echo "❌ MCP 库安装失败"
    exit 1
fi

echo ""
echo "💡 提示："
echo "- 查看 'MCP集成配置指南.md' 了解详细集成步骤"
echo "- 或使用HTTP API方式: python server/mcp_http_server.py"
