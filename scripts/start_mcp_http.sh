#!/bin/bash
# MCP HTTP API启动脚本

echo "🚀 Starting MCP HTTP API Server..."

# 检查端口占用
if curl -f http://localhost:9000/ &>/dev/null; then
    echo "⚠️  端口9000已被占用，请检查是否已运行"
    echo "   尝试: docker-compose ps"
fi

echo "🔧 启动MCP HTTP API服务器..."
echo "访问地址: http://localhost:9000"
echo ""
echo "📋 可用的MCP工具端点："
echo "   GET  /           - API信息"
echo "   GET  /mcp/tools   - 工具列表"  
echo "   POST /mcp/document_ocr - PDF文档识别"
echo "   POST /mcp/analyze_image - 图片分析"
echo "   POST /mcp/extract_structured_data - 结构化数据提取"
echo "   POST /mcp/batch_process - 批量文档处理"
echo "   POST /mcp/tool   - 通用工具调用"
echo ""

# 设置导出环境
export PYTHONPATH=/app

# 启动服务器
python server/mcp_http_server.py
