#!/usr/bin/env python3
"""
测试新增的MCP功能
"""

import requests
import json
from pathlib import Path

SERVER_URL = "http://192.168.10.200:9000"

def test_new_endpoints():
    """测试新的端点"""
    
    print("🔍 测试新的专门功能端点")
    print("=" * 50)
    
    # 1. 测试PDF文档识别端点
    print("1️⃣ 测试 PDF OCR 端点...")
    try:
        response = requests.get(f"{SERVER_URL}/mcp/pdf_ocr")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 404:
            print("   ⚠️ 端点尚未可用（请重启容器应用代码）")
        elif response.status_code == 422:
            print("   ✅ 端点可用 (缺少数据模型验证)")
    except requests.exceptions.ConnectionError:
        print("   ❌ 无法连接终端")
    
    # 2. 测试图片描述端点
    print("2️⃣ 测试 图片描述 端点...")
    try:
        response = requests.get(f"{SERVER_URL}/mcp/image_description")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 404:
            print("   ⚠️ 端点尚未可用")
        elif response.status_code == 422:
            print("   ✅ 端点可用")
    except Exception as e:
        print(f"   ⚠️ {str(e)}")
    
    # 3. 测试发票提取端点
    print("3️⃣ 测试 发票提取 端点...")
    try:
        response = requests.get(f"{SERVER_URL}/mcp/invoice_extraction")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 404:
            print("   ⚠️ 端点尚未可用")
        elif response.status_code == 422:
            print("   ✅ 端点可用")
    except Exception as e:
        print(f"   ⚠️ {str(e)}")
    
    # 4. 测试批量统一文档端点
    print("4️⃣ 测试 批量统一文档 端点...")
    try:
        response = requests.get(f"{SERVER_URL}/mcp/batch_unified")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 404:
            print("   ⚠️ 端点尚未可用")
        elif response.status_code == 422:
            print("   ✅ 端点可用")
    except Exception as e:
        print(f"   ⚠️ {str(e)}")
    
    print()


def test_tools_list():
    """测试可选工具列表"""
    
    print("🔧 测试可选工具列表...")
    try:
        response = requests.get(f"{SERVER_URL}/mcp/tools")
        if response.status_code == 200:
            tools = response.json()
            new_tools = []
            for tool in tools.get("tools", []):
                if any(keyword in tool.get("name", "").lower() for keyword in 
                      ["pdf", "description", "invoice", "batch"]):
                    new_tools.append(tool)
            
            if new_tools:
                print("✅ 新功能工具已添加:")
                for tool in new_tools:
                    print(f"  - {tool['name']}: {tool['description']}")
            else:
                print("⚠️ 未在工具列表中检测到新功能")
        else:
            print("❌ 无法获取工具列表")
    except Exception as e:
        print(f"⚠️ 列表测试失败: {e}")


def test_sample_request():
    """测试示例请求（如果有示例文件）"""
    
    print("📬 测试示例请求...")
    try:
        # 测试图片描述（无文件）
        test_payload = {
            "file_data": "test",
            "filename": "test.jpg",
            "description_type": "describe"
        }
        
        response = requests.post(
            f"{SERVER_URL}/mcp/image_description",
            json=test_payload,
            timeout=5
        )
        
        print(f"示例请求状态: HTTP {response.status_code}")
        
        if response.status_code == 422:
            print("✅ 端点验证正常，缺少有效文件数据")
        elif response.status_code == 404:
            print("⚠️ 端点未找到（需要代码部署）")
        else:
            print(f"ℹ️ 响应: {response.text[:100]}")
    
    except Exception as e:
        print(f"⚠️ 样例失败: {e}")


def main():
    """自动测试完成"""
    
    print("🚀 MCP 新专门功能测试")
    print("=" * 60)
    print("🏠 服务地址:", SERVER_URL)
    print()
    
    test_new_endpoints()
    test_tools_list()
    test_sample_request()
    
    print("💡 使用提示:")
    print("- Python 代码: from remote_mcp_client import *")
    print("- 直接在脚本中调用: ")
    print("  client = RemoteVisionAIClient('http://192.168.10.200:9000')")
    print()
    
    print("📄 请运行以下示例:")
    print("  python 专门功能使用示例.py")
    print()

if __name__ == "__main__":
    main()
