#!/usr/bin/env python3
"""
远程 Vision AI MCP 客户端配置示例
针对 http://192.168.10.200:9000 的服务地址
"""

import requests
import base64
import os
from pathlib import Path
import json


class RemoteVisionAIClient:
    """远程 Vision AI MCP HTTP 客户端"""
    
    def __init__(self, base_url="http://192.168.10.200:9000"):
        """初始化远程 MCP 客户端"""
        self.base_url = base_url
        self.session = requests.Session()
        # 设置超时时间适合远程连接
        self.timeout = 300  # 5分钟超时
    
    def get_available_tools(self):
        """获取可用的工具"""
        try:
            response = self.session.get(
                f"{self.base_url}/mcp/tools",
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"获取工具失败: HTTP {response.status_code}"}
        except requests.exceptions.ConnectTimeout as e:
            return {"error": f"连接超时: {str(e)} - 请检查网络连接"}
        except requests.exceptions.ConnectionError as e:
            return {"error": f"连接错误: {str(e)} - 请检查服务器地址和端口"}
        except Exception as e:
            return {"error": f"连接错误: {str(e)}"}
    
    def get_configured_models(self):
        """获取已配置的模型列表"""
        try:
            response = self.session.get(
                f"{self.base_url}/mcp/models",
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"获取模型列表失败: HTTP {response.status_code}"}
        except requests.exceptions.ConnectTimeout as e:
            return {"error": f"连接超时: {str(e)} - 请检查网络连接"}
        except requests.exceptions.ConnectionError as e:
            return {"error": f"连接错误: {str(e)} - 请检查服务器地址和端口"}
        except Exception as e:
            return {"error": f"连接错误: {str(e)}"}
    
    def analyze_image(self, image_path, analysis_type="describe", custom_prompt=None, model_id=None):
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
            if model_id:
                payload["model_id"] = model_id
            
            response = self.session.post(
                f"{self.base_url}/mcp/analyze_image",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                return {"error": f"分析失败: HTTP {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"处理出错: {str(e)}"}
    
    def process_pdf(self, pdf_path, max_pages=10, prompt=None, model_id=None):
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
            if model_id:
                payload["model_id"] = model_id
            
            response = self.session.post(
                f"{self.base_url}/mcp/document_ocr",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                return {"error": f"处理失败: HTTP {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"处理出错: {str(e)}"}
    
    def extract_structured_data(self, file_path, extraction_target="invoice", model_id=None):
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
            
            if model_id:
                payload["model_id"] = model_id
            
            response = self.session.post(
                f"{self.base_url}/mcp/extract_structured_data",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                return {"error": f"提取失败: HTTP {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"处理出错: {str(e)}"}
    
    # 新增的专门功能方法
    
    def pdf_document_ocr(self, pdf_path, max_pages=10, prompt=None, model_id=None):
        """专门的PDF文档OCR识别"""
        try:
            if not os.path.exists(pdf_path):
                return {"error": f"文件不存在: {pdf_path}"}
            
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
            if model_id:
                payload["model_id"] = model_id
            
            response = self.session.post(
                f"{self.base_url}/mcp/pdf_ocr",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"PDF OCR失败: HTTP {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"处理出错: {str(e)}"}
    
    def image_description(self, image_path, description_type="describe", custom_prompt=None, model_id=None):
        """专门的图片内容描述"""
        try:
            if not os.path.exists(image_path):
                return {"error": f"文件不存在: {image_path}"}
            
            with open(image_path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode()
            
            filename = Path(image_path).name
            payload = {
                "file_data": file_data,
                "filename": filename,
                "description_type": description_type
            }
            
            if custom_prompt:
                payload["custom_prompt"] = custom_prompt
            if model_id:
                payload["model_id"] = model_id
            
            response = self.session.post(
                f"{self.base_url}/mcp/image_description",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"图片描述失败: HTTP {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"处理出错: {str(e)}"}
    
    def invoice_extraction(self, file_path, extraction_schema=None, model_id=None):
        """发票信息结构化提取"""
        try:
            if not os.path.exists(file_path):
                return {"error": f"文件不存在: {file_path}"}
            
            with open(file_path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode()
            
            filename = Path(file_path).name
            payload = {
                "file_data": file_data,
                "filename": filename
            }
            
            if extraction_schema:
                payload["extraction_schema"] = extraction_schema
            if model_id:
                payload["model_id"] = model_id
            
            response = self.session.post(
                f"{self.base_url}/mcp/invoice_extraction",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"发票提取失败: HTTP {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"处理出错: {str(e)}"}
    
    def batch_unified_document(self, documents, process_type="ocr", merge_to_single=True, 
                             custom_prompt=None, model_id=None):
        """批量文档或图片转统一文档"""
        try:
            encoded_docs = []
            for doc_path in documents:
                if not os.path.exists(doc_path):
                    return {"error": f"文件不存在: {doc_path}"}
                
                with open(doc_path, 'rb') as f:
                    file_data = base64.b64encode(f.read()).decode()
                
                encoded_docs.append({
                    "file_data": file_data,
                    "filename": Path(doc_path).name
                })
            
            payload = {
                "documents": encoded_docs,
                "process_type": process_type,
                "merge_to_single": merge_to_single
            }
            
            if custom_prompt:
                payload["custom_prompt"] = custom_prompt
            if model_id:
                payload["model_id"] = model_id
            
            response = self.session.post(
                f"{self.base_url}/mcp/batch_unified",
                json=payload,
                timeout=self.timeout * 2  # 批处理需要更长时间
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"批量处理失败: HTTP {response.status_code} - {response.text}"}
                
        except Exception as e:
            return {"error": f"处理出错: {str(e)}"}


# 使用示例和配置
def main():
    """演示远程MCP服务使用方法"""
    
    print("🌐 远程 Vision AI MCP 客户端演示")
    print("=" * 50)
    
    # 初始化远程客户端
    client = RemoteVisionAIClient("http://192.168.10.200:9000")
    
    # 检查连接
    print("🔍 检查远程服务连接...")
    tools = client.get_available_tools()
    
    if "error" in tools:
        print(f"❌ 连接失败: {tools['error']}")
        print("\n💡 解决方案:")
        print("1. 检查服务器地址是否正确")
        print("2. 确保端口9000可以访问")
        print("3. 检查防火墙设置")
        return
    
    print(f"✅ 连接成功!")
    print(f"📋 可用工具: {json.dumps(tools, indent=2, ensure_ascii=False)}")
    
    print("\n📝 使用示例:")
    print("# 方法一：直接配置URL")
    print("client = RemoteVisionAIClient('http://192.168.10.200:9000')")
    print("result = client.analyze_image('image.jpg')")
    print("")
    print("# 方法二：环境变量配置")
    print("import os")
    print("VISION_AI_URL = os.getenv('VISION_AI_URL', 'http://192.168.10.200:9000')")
    print("client = RemoteVisionAIClient(VISION_AI_URL)")
    

def test_connection(server_url="http://192.168.10.200:9000"):
    """测试远程连接"""
    try:
        response = requests.get(f"{server_url}/", timeout=10)
        if response.status_code == 200:
            print(f"✅ 服务可访问: {server_url}")
            service_info = response.json()
            print(f"📊 服务信息: {service_info}")
            return True
        else:
            print(f"❌ 服务返回错误: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectTimeout:
        print(f"❌ 连接超时: {server_url}")
        return False
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接: {server_url}")
        print("  请检查服务器是否运行在那个地址")
        return False
    except Exception as e:
        print(f"❌ 连接错误: {str(e)}")
        return False


if __name__ == "__main__":
    # 测试连接
    test_connection()
    print("\n" + "="*50)
    
    # 演示客户端使用
    main()
