#!/usr/bin/env python3
"""
MCP 专门功能使用示例
使用您提出的五种专门功能：
1. PDF文档识别
2. 图片内容描述
3. 结构化数据提取（发票信息）
4. 批量文档或图片转统一文档
"""

from remote_mcp_client import RemoteVisionAIClient
import os
from pathlib import Path

def example_pdf_ocr():
    """1. PDF文档识别示例"""
    print("📄 PDF文档识别示例")
    print("=" * 50)
    
    client = RemoteVisionAIClient("http://192.168.10.200:9000")
    
    # 使用默认模型
    result = client.pdf_document_ocr("document.pdf", max_pages=5)
    print(f"默认模型结果: {result.get('output', '处理失败')[:100]}...")
    
    # 指定特定模型
    result2 = client.pdf_document_ocr(
        "document.pdf", 
        model_id="1c2361e3-d011-4417-9139-b30a8acc915a",  # yanse-minicpm
        max_pages=3
    )
    print(f"指定模型结果: {result2.get('output', '处理失败')[:100]}...")
    
    print("-" * 30)


def example_image_description():
    """2. 图片内容描述示例"""
    print("🖼️ 图片内容描述示例")
    print("=" * 50)
    
    client = RemoteVisionAIClient("http://192.168.10.200:9000")
    
    # 基础描述
    result = client.image_description("photo.jpg", description_type="describe")
    print(f"基础描述: {result.get('output', '处理失败')[:100]}...")
    
    # 详细描述
    result2 = client.image_description(
        "photo.jpg", 
        description_type="detailed",
        model_id="03eb09a7-c29a-4f07-bb12-d67c4cfa294a"  # gemini模型
    )
    print(f"详细描述: {result2.get('output', '处理失败')[:100]}...")
    
    # 结构化描述
    result3 = client.image_description(
        "photo.jpg", 
        description_type="structured",
        model_id="1c2361e3-d011-4417-9139-b30a8acc915a"
    )
    print(f"结构化描述: {result3.get('output', '处理失败')[:100]}...")
    
    print("-" * 30)


def example_invoice_extraction():
    """3. 发票信息提取示例"""
    print("🧾 发票信息提取示例")
    print("=" * 50)
    
    client = RemoteVisionAIClient("http://192.168.10.200:9000")
    
    # 基础发票提取
    result = client.invoice_extraction("invoice.pdf", 
        model_id="2d1da23b-1e1b-4c8d-a465-d18c07603929"  # OCR专用模型
    )
    print(f"发票信息提取: {result.get('extracted_data', '提取失败')[:100]}...")
    
    # 自定义提取字段
    custom_schema = {
        "items": ["product_name", "quantity", "price"],
        "vendor_info": ["name", "address", "tax_number"]
    }
    
    result2 = client.invoice_extraction("invoice.jpg", 
        extraction_schema=custom_schema,
        model_id="03eb09a7-c29a-4f07-bb12-d67c4cfa294a"
    )
    print(f"自定义提取: {result2.get('extracted_data', '提取失败')[:100]}...")
    
    print("-" * 30)


def example_batch_unified_document():
    """4. 批量文档转统一文档示例"""
    print("📚 批量文档/图片转统一文档示例")
    print("=" * 50)
    
    client = RemoteVisionAIClient("http://192.168.10.200:9000")
    
    # 文档列表
    documents = [
        "mulction_penalty_inspection_invite_memento.pdf",
        "sample.jpg",
        "sample2.png"
    ]
    
    # OCR处理并合并
    result = client.batch_unified_document(
        documents, 
        process_type="ocr",
        merge_to_single=True,
        model_id="1c2361e3-d011-4417-9139-b30a8acc915a"
    )
    
    if result.get('success'):
        print(f"处理成功: {result.get('message')}")
        if result.get('merged_output'):
            print(f"统一文档: {result.get('merged_output')}")
    else:
        print(f"处理失败: {result.get('error')}")
    
    # 图片描述并合并
    result2 = client.batch_unified_document(
        ["image1.jpg", "image2.png", "document.pdf"], 
        process_type="describe",
        merge_to_single=True,
        model_id="03eb09a7-c29a-4f07-bb12-d67c4cfa294a"
    )
    
    print("-" * 30)


def example_advanced_usage():
    """5. 高级用法示例 - 综合处理"""
    print("🎯 综合处理示例")
    print("=" * 50)
    
    client = RemoteVisionAIClient("http://192.168.10.200:9000")
    
    print("📋 可用模型:")
    models = client.get_configured_models()
    if models and "models" in models:
        for model in models["models"][:5]:  # 显示前5个模型
            print(f"  - {model.get('name')}: {model.get('model_type')}")
    
    print("\n🔧 功能示例:")
    print("1. PDF识别 + 模型指定")
    print("   client.pdf_document_ocr('doc.pdf', model_id='模型ID')")
    
    print("2. 多类型图片描述")
    print("   client.image_description('img.jpg', description_type='detailed')")
    
    print("3. 发票字段提取")
    print("   client.invoice_extraction('invoice.pdf', extraction_schema={...})")
    
    print("4. 批量多米诺文档合并")
    print("   client.batch_unified_document(docs, merge_to_single=True)")
    
    print("-" * 30)


if __name__ == "__main__":
    print("🎉 MCP 五种专门功能演示")
    print("=" * 60)
    print("功能分为:")
    print("1. 📄 PDF文档识别")
    print("2. 🖼️ 图片内容描述")
    print("3. 🧾 发票信息提取")
    print("4. 📚 批量文档合并")
    print("5. 🎯 综合处理")
    print("\n")
    
    try:
        example_pdf_ocr()
        example_image_description()
        example_invoice_extraction()
        example_batch_unified_document()
        example_advanced_usage()
        
        print("\n💡 使用说明:")
        print("- remote_mcp_client.py 已经包含新功能")
        print("- 所有方法都支持指定 model_id 来选择特定模型")
        print("- 支持自定义提示词和提取字段")
        print("- 执行: python 专门功能使用示例.py")
        
    except Exception as e:
        print(f"❌ 示例执行出错: {e}")
        print("🔧 请确保远程服务器正在运行并可用")
