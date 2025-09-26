#!/usr/bin/env python3
"""
MCP (Model Context Protocol) 服务器
为LLM提供视觉处理和多模态能力
支持PDF OCR、图片分析、文档结构化提取等功能
"""

import asyncio
import json
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
import base64

try:
    from mcp.server import Server
    from mcp.types import (
        CallToolRequest,
        CallToolResult,
        Text,
        Tool,
        CallToolError,
        McpError,
    )
    from mcp.server.stdio import stdio_server
except ImportError:
    # 如果MCP库未安装，提供fallback
    print("警告: MCP库未安装，请运行: pip install mcp")
    sys.exit(1)

# 导入现有项目的处理函数
try:
    from server.main import (
        process_pdf_with_progress,
        process_single_image,
        run_mlx_vlm_generate,
        run_api_generate,
        DEFAULT_PROMPTS,
        DEFAULT_MODEL_PATH,
        UPLOAD_DIR,
        OUTPUT_DIR,
        save_markdown,
        clean_output_text
    )
except ImportError:
    # 如果直接运行时导入失败，尝试相对导入
    from main import (
        process_pdf_with_progress,
        process_single_image,
        run_mlx_vlm_generate,
        run_api_generate,
        DEFAULT_PROMPTS,
        DEFAULT_MODEL_PATH,
        UPLOAD_DIR,
        OUTPUT_DIR,
        save_markdown,
        clean_output_text
    )

# 配置服务器
app = Server("vision-ai-mcp")

@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    """返回可用的MCP工具列表"""
    return [
        Tool(
            name="document_ocr",
            description="OCR文档识别工具 - 将PDF文档转换为可编辑的文本，保持原有格式",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_data": {
                        "type": "string", 
                        "description": "Base64编码的文件内容"
                    },
                    "filename": {
                        "type": "string",
                        "description": "原始文件名，如: invoice.pdf"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "自定义处理提示词，默认: PDF文本提取",
                        "default": "请仔细识别并提取这个PDF页面的所有文本内容，按照原文档结构排版"
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": "最大处理页数",
                        "default": 10
                    }
                },
                "required": ["file_data", "filename"]
            }
        ),
        Tool(
            name="analyze_image", 
            description="图片分析工具 - 描述图片内容、分析图像元素和视觉构成",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_data": {
                        "type": "string",
                        "description": "Base64编码的图片内容"
                    },
                    "filename": {
                        "type": "string", 
                        "description": "图片文件名，如: photo.jpg"
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["describe", "invoice", "custom"],
                        "description": "分析类型：describe=描述内容、invoice=信息提取、custom=自定义",
                        "default": "describe"
                    },
                    "custom_prompt": {
                        "type": "string",
                        "description": "自定义分析提示词（仅当analysis_type=custom时使用）"
                    }
                },
                "required": ["file_data", "filename"]
            }
        ),
        Tool(
            name="extract_structured_data",
            description="结构化数据提取工具 - 从文档中提取特定信息，如发票详情、表单数据等",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_data": {
                        "type": "string",
                        "description": "Base64编码的文件内容"
                    },
                    "filename": {
                        "type": "string",
                        "description": "文件名"
                    },
                    "extraction_target": {
                        "type": "string",
                        "enum": ["invoice", "form", "contract", "receipt"],
                        "description": "数据提取目标类型"
                    },
                    "custom_schema": {
                        "type": "object",
                        "description": "自定义数据提取结构Schema"
                    }
                },
                "required": ["file_data", "filename", "extraction_target"]
            }
        ),
        Tool(
            name="batch_process_documents",
            description="批量文档处理工具 - 支持批量处理多个文档并合并结果",
            inputSchema={
                "type": "object",
                "properties": {
                    "documents": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file_data": {"type": "string"},
                                "filename": {"type": "string"}
                            },
                            "required": ["file_data", "filename"]
                        },
                        "description": "待处理的文档列表"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "统一的处理提示词"
                    },
                    "merge_results": {
                        "type": "boolean",
                        "description": "是否将结果合并到单个文档",
                        "default": False
                    }
                },
                "required": ["documents", "prompt"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """处理MCP工具调用请求"""
    try:
        if name == "document_ocr":
            return await handle_document_ocr(arguments)
        elif name == "analyze_image":
            return await handle_analyze_image(arguments)
        elif name == "extract_structured_data":
            return await handle_extract_structured_data(arguments)
        elif name == "batch_process_documents":
            return await handle_batch_process(arguments)
        else:
            raise McpError("INVALID_PARAMS", f"未知的工具名称: {name}")
    except Exception as e:
        raise CallToolError(name, str(e), f"工具调用失败: {str(e)}")

async def handle_document_ocr(arguments: Dict[str, Any]) -> CallToolResult:
    """处理PDF OCR文档识别"""
    file_data = arguments.get("file_data")
    filename = arguments.get("filename")
    custom_prompt = arguments.get("prompt", DEFAULT_PROMPTS.get("pdf_extract", ""))
    max_pages = arguments.get("max_pages", 10)
    
    # 解码base64文件内容
    file_bytes = base64.b64decode(file_data)
    
    # 保存临时文件
    temp_path = UPLOAD_DIR / f"temp_{uuid.uuid4()}_{filename}"
    temp_path.write_bytes(file_bytes)
    
    try:
        base_name = Path(filename).stem
        
        # 调用现有的PDF处理函数
        out_path, md_content = process_pdf_with_progress(
            temp_path, custom_prompt, DEFAULT_MODEL_PATH, 1024, 0.0, 
            base_name, max_pages
        )
        
        result = {
            "success": True,
            "document_name": filename,
            "extracted_text": md_content,
            "output_file": f"/outputs/{Path(out_path).name}",
            "message": f"PDF文档 '{filename}' 处理完成，已提取 {len(md_content)} 字符的文本内容"
        }
        
        return CallToolResult(
            content=[Text(type="text", text=json.dumps(result, ensure_ascii=False))]
        )
    
    finally:
        # 清理临时文件
        temp_path.unlink(missing_ok=True)

async def handle_analyze_image(arguments: Dict[str, Any]) -> CallToolResult:
    """处理图片内容分析"""
    file_data = arguments.get("file_data")
    filename = arguments.get("filename")
    analysis_type = arguments.get("analysis_type", "describe")
    custom_prompt = arguments.get("custom_prompt")
    
    # 解码base64文件内容
    file_bytes = base64.b64decode(file_data)
    
    # 保存临时文件
    temp_path = UPLOAD_DIR / f"temp_{uuid.uuid4()}_{filename}"
    temp_path.write_bytes(file_bytes)
    
    try:
        # 确定要使用的提示词
        if analysis_type == "custom" and custom_prompt:
            prompt = custom_prompt
        elif analysis_type == "invoice":
            prompt = DEFAULT_PROMPTS.get("invoice", "")
        elif analysis_type == "describe":
            prompt = DEFAULT_PROMPTS.get("describe", "")
        else:
            prompt = DEFAULT_PROMPTS.get("describe", "")
        
        base_name = Path(filename).stem
        
        # 调用现有的图片处理函数
        out_path, analysis_result = process_single_image(
            temp_path, prompt, DEFAULT_MODEL_PATH, 1024, 0.0, base_name
        )
        
        result = {
            "success": True,
            "image_name": filename,
            "analysis": analysis_result,
            "analysis_type": analysis_type,
            "output_file": f"/outputs/{Path(out_path).name}",
            "message": f"图片 '{filename}' 分析完成"
        }
        
        return CallToolResult(
            content=[Text(type="text", text=json.dumps(result, ensure_ascii=False))]
        )
    
    finally:
        # 清理临时文件
        temp_path.unlink(missing_ok=True)

async def handle_extract_structured_data(arguments: Dict[str, Any]) -> CallToolResult:
    """处理结构化数据提取"""
    file_data = arguments.get("file_data")
    filename = arguments.get("filename")
    extraction_target = arguments.get("extraction_target")
    custom_schema = arguments.get("custom_schema", {})
    
    # 根据提取目标选择提示词
    target_prompts = {
        "invoice": "请提取该发票的所有关键信息，包含：发票号码、开票日期、销售方、购买方、商品/服务明细、总金额、税额等",
        "form": "请提取该表单的所有字段信息，保持结构层次",
        "contract": "请提取该合同的关键条款信息，包含：合同双方、主要条款、期限、金额等",
        "receipt": "请提取该收据/小票的所有信息，包含：商家、时间、商品、金额等"
    }
    
    prompt = target_prompts.get(extraction_target, "请从该文档中提取结构化信息")
    
    # 解码并处理文件
    file_bytes = base64.b64decode(file_data)
    temp_path = UPLOAD_DIR / f"temp_{uuid.uuid4()}_{filename}"
    temp_path.write_bytes(file_bytes)
    
    try:
        base_name = Path(filename).stem
        
        # 判断文件类型并处理
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            out_path, content = process_pdf_with_progress(
                temp_path, prompt, DEFAULT_MODEL_PATH, 1024, 0.0, base_name
            )
        else:
            out_path, content = process_single_image(
                temp_path, prompt, DEFAULT_MODEL_PATH, 1024, 0.0, base_name
            )
        
        result = {
            "success": True,
            "document_name": filename,
            "extraction_target": extraction_target,
            "structured_data": content,
            "output_file": f"/outputs/{Path(out_path).name}",
            "message": f"文档 {filename} 的结构化数据提取完成"
        }
        
        return CallToolResult(
            content=[Text(type="text", text=json.dumps(result, ensure_ascii=False))]
        )
    
    finally:
        temp_path.unlink(missing_ok=True)

async def handle_batch_process(arguments: Dict[str, Any]) -> CallToolResult:
    """处理批量文档处理"""
    documents = arguments.get("documents", [])
    prompt = arguments.get("prompt")
    merge_results = arguments.get("merge_results", False)
    
    processed_results = []
    
    for doc in documents:
        file_data = doc["file_data"]
        filename = doc["filename"]
        
        # 解码文件
        file_bytes = base64.b64decode(file_data)
        temp_path = UPLOAD_DIR / f"temp_{uuid.uuid4()}_{filename}"
        temp_path.write_bytes(file_bytes)
        
        try:
            base_name = Path(filename).stem
            suffix = Path(filename).suffix.lower()
            
            # 处理文档
            if suffix == ".pdf":
                out_path, content = process_pdf_with_progress(
                    temp_path, prompt, DEFAULT_MODEL_PATH, 1024, 0.0, base_name
                )
            else:
                out_path, content = process_single_image(
                    temp_path, prompt, DEFAULT_MODEL_PATH, 1024, 0.0, base_name
                )
            
            processed_results.append({
                "filename": filename,
                "content": content,
                "output_file": f"/outputs/{Path(out_path).name}"
            })
            
        finally:
            temp_path.unlink(missing_ok=True)
    
    # 如果要求合并结果
    if merge_results and processed_results:
        merged_content = ["# 批量处理结果合并\n\n"]
        
        for idx, result in enumerate(processed_results, 1):
            merged_content.append(f"## {idx}. {result['filename']}\n\n")
            merged_content.append(result['content'])
            merged_content.append("\n\n---\n\n")
        
        timestamp = __import__('time').strftime("%Y%m%d_%H%M%S")
        merged_filename = f"batch_merged_{timestamp}"
        merged_path = save_markdown("".join(merged_content), merged_filename)
        
        result = {
            "success": True,
            "batch_size": len(documents),
            "results": processed_results,
            "merged": merge_results,
            "merged_output": f"/outputs/{Path(merged_path).name}" if merge_results else None,
            "message": f"批量处理完成：处理了 {len(documents)} 个文档"
        }
    else:
        result = {
            "success": True,
            "batch_size": len(documents),
            "results": processed_results,
            "merged": False,
            "message": f"批量处理完成：处理了 {len(documents)} 个文档"
        }
    
    return CallToolResult(
        content=[Text(type="text", text=json.dumps(result, ensure_ascii=False))]
    )

async def main():
    """运行MCP服务器"""
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1])

if __name__ == "__main__":
    asyncio.run(main())
