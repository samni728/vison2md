#!/usr/bin/env python3
"""
Vision AI MCP 客户端示例
展示如何在自己的项目中使用 Vision AI 的 MCP 服务器
"""

import requests
import base64
import os
from pathlib import Path
import json


class VisionAIClient:
    """Vision AI MCP HTTP 客户端"""
    
    def __init__(self, base_url="http://localhost:9000"):
        """初始化 MCP 客户端"""
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_available_tools(self):
        """获取可用的工具"""
        try:
            response = self.session.get(f"{self.base_url}/mcp/tools")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"获取工具失败: HTTP {response.status_code}"}
        except Exception as e:
            return {"error": f"连接错误: {str(e)}"}
    
    def analyze_image(self, image_path, analysis_type="describe", custom_prompt=None):
        """分析图片内容"""
        try:
            if not os.path.exists(image_path):
                return {"error": f"文件不存在: {image_path}"}
            
            # 读取并编码文件
            with open(image_path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode()
            
            filename = Path(image_path).name
            
            payload = {
                "file_data": file_data,
                "filename": filename,
                "analysis_type": analysis_type
            }
            
            if custom_prompt:
                payload["custom_prompt"] = custom_prompt
            
            response = self.session.post(f"{self.base_url}/mcp/analyze_image", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                return {"error": f"分析失败: HTTP {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"处理出错: {str(e)}"}
    
    def process_pdf(self, pdf_path, max_pages=10, prompt=None):
        """处理PDF文档OCR"""
        try:
            if not os.path.exists(pdf_path):
                return {"error": f"文件不存在: {pdf_path}"}
            
            # 读取并编码文件
            with open(pdf_path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode()
            
            filename = Path(pdf_path).name
            
            payload = {
                "file_data": file_data,
                "filename": filename,
                "max_pages": max_pages
            }
            
            if prompt:
                payload["prompt"] = prompt
            
            response = self.session.post(f"{self.base_url}/mcp/document_ocr", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                return {"error": f"处理失败: HTTP {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"处理出错: {str(e)}"}
    
    def extract_structured_data(self, file_path, extraction_target="invoice"):
        """从文件中提取结构化数据"""
        try:
            if not os.path.exists(file_path):
                return {"error": f"文件不存在: {file_path}"}
            
            # 读取并编码文件
            with open(file_path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode()
            
            filename = Path(file_path).name
            
            payload = {
                "file_data": file_data,
                "filename": filename,
                "extraction_target": extraction_target
            }
            
            response = self.session.post(f"{self.base_url}/mcp/extract_structured_data", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                return {"error": f"提取失败: HTTP {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"处理出错: {str(e)}"}
    
    def batch_process(self, file_paths, prompt="分析和提取关键信息", merge_results=False):
        """批量处理多个文件"""
        try:
            documents = []
            
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    return {"error": f"文件不存在: {file_path}"}
                
                with open(file_path, 'rb') as f:
                    file_data = base64.b64encode(f.read()).decode()
                
                documents.append({
                    "file_data": file_data,
                    "filename": Path(file_path).name
                })
            
            payload = {
                "documents": documents,
                "prompt": prompt,
                "merge_results": merge_results
            }
            
            response = self.session.post(f"{self.base_url}/mcp/batch_process", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                return {"error": f"批量处理失败: HTTP {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"处理出错: {str(e)}"}


# 使用示例
def main():
    """示例：使用 Vision AI MCP 客户端"""
    
    print("🚀 Vision AI MCP 客户端示例演示")
    print("=" * 40)
    
    # 初始化客户端
    client = VisionAIClient("http://localhost:9000")
    
    # 检查服务状态
    tools = client.get_available_tools()
    print(f"可用工具: {json.dumps(tools, indent=2, ensure_ascii=False)}")
    
    print("\n📝 使用示例：")
    print("1. 分析图片：client.analyze_image('path/to/image.jpg')")
    print("2. 处理PDF：client.process_pdf('path/to/document.pdf')")
    print("3. 提取结构数据：client.extract_structured_data('path/to/invoice.pdf')")
    print("4. 批量处理：client.batch_process(['file1.pdf', 'file2.jpg'])")
    
    print("\n🔧 配置提示：")
    print("- 确保 Vision AI MCP HTTP API 运行在 localhost:9000")
    print("- 运行：python server/mcp_http_server.py")
    print("- 或启动Docker服务：docker-compose up -d")


if __name__ == "__main__":
    main()
