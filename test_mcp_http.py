#!/usr/bin/env python3
"""
测试MCP HTTP API的示例脚本
"""

import requests
import json
import base64
from pathlib import Path

def test_mcp_api():
    """测试MCP HTTP API端点"""
    
    base_url = "http://localhost:9000"
    
    print("🔍 测试MCP HTTP API...")
    
    # 测试1：检查API根端点
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ API根端点: {response.status_code}")
        api_info = response.json()
        print(f"   服务: {api_info.get('service')}")
        print(f"   工具: {api_info.get('tools')}")
    except Exception as e:
        print(f"❌ API根端点错误: {e}")
        return
    
    # 测试2：检查可用工具
    try:
        response = requests.get(f"{base_url}/mcp/tools")
        print(f"✅ 可用工具: {response.status_code}")
        tools = response.json()
        print(f"   工具数量: {len(tools.get('tools', []))}")
        for tool in tools.get('tools', []):
            print(f"   - {tool['name']}: {tool['description']}")
    except Exception as e:
        print(f"❌ 工具列表错误: {e}")
    
    print("\n🎯 使用示例（需要实际文件数据）:")
    print("""
    # 示例：调用图片分析
    curl -X POST "http://localhost:9000/mcp/analyze_image" \\
      -H "Content-Type: application/json" \\
      -d '{
        "file_data": "base64_encoded_image",
        "filename": "test.jpg",
        "analysis_type": "describe"
      }'
    
    # 示例：调用PDF文档识别
    curl -X POST "http://localhost:9000/mcp/document_ocr" \\
      -H "Content-Type: application/json" \\
      -d '{
        "file_data": "base64_encoded_pdf",
        "filename": "test.pdf",
        "max_pages": 5
      }'
    """)
    
    print("\n🚀 服务器启动方式:")
    print("docker-compose up -d  # 8000端口(Web) + 9000端口(MCP HTTP)")
    print("python server/mcp_http_server.py  # 直接启动MCP HTTP API")

if __name__ == "__main__":
    test_mcp_api()
