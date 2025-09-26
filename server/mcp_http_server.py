#!/usr/bin/env python3
"""
MCP HTTP API 服务器
将MCP工具通过HTTP端点暴露，支持远程调用
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import base64
import asyncio

# 导入现有项目的处理函数
try:
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
except ImportError:
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

# 创建HTTP版本的MCP API
app = FastAPI(title="Vision AI MCP HTTP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型定义
class DocumentOCRRequest(BaseModel):
    file_data: str  # Base64编码的文件内容
    filename: str
    prompt: Optional[str] = None
    max_pages: int = 10

class ImageAnalysisRequest(BaseModel):
    file_data: str  # Base64编码的图片内容
    filename: str
    analysis_type: str = "describe"
    custom_prompt: Optional[str] = None

class StructuredDataRequest(BaseModel):
    file_data: str  # Base64编码的文件内容
    filename: str
    extraction_target: str  # invoice, form, contract, receipt
    custom_schema: Optional[Dict] = None

class BatchProcessRequest(BaseModel):
    documents: List[Dict[str, str]]  # [{"file_data": "...", "filename": "..."}]
    prompt: str
    merge_results: bool = False

class MCPToolRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]

# MCP工具实现
async def handle_document_ocr(data: DocumentOCRRequest) -> Dict[str, Any]:
    """处理PDF OCR文档识别"""
    import tempfile
    import uuid
    import base64
    from pathlib import Path
    
    # 解码base64文件内容
    file_bytes = base64.b64decode(data.file_data)
    
    # 保存临时文件
    temp_path = UPLOAD_DIR / f"mcp_temp_{uuid.uuid4().hex}_{data.filename}"
    temp_path.write_bytes(file_bytes)
    
    try:
        base_name = Path(data.filename).stem
        prompt = data.prompt or DEFAULT_PROMPTS.get("pdf_extract", "")
        
        # 调用现有的PDF处理函数
        out_path, md_content = process_pdf_with_progress(
            temp_path, prompt, DEFAULT_MODEL_PATH, 1024, 0.0, 
            base_name, data.max_pages
        )
        
        result = {
            "success": True,
            "tool": "document_ocr",
            "input": data.filename,
            "output": md_content,
            "file_output": f"/outputs/{Path(out_path).name}",
            "message": f"PDF文档 '{data.filename}' 处理完成"
        }
        
        return result
    
    finally:
        # 清理临时文件
        temp_path.unlink(missing_ok=True)

async def handle_image_analysis(data: ImageAnalysisRequest) -> Dict[str, Any]:
    """处理图片内容分析"""
    import tempfile
    import uuid
    import base64
    from pathlib import Path
    
    # 解码base64文件内容
    file_bytes = base64.b64decode(data.file_data)
    
    # 保存临时文件
    temp_path = UPLOAD_DIR / f"mcp_temp_{uuid.uuid4().hex}_{data.filename}"
    temp_path.write_bytes(file_bytes)
    
    try:
        # 确定要使用的提示词
        if data.analysis_type == "custom" and data.custom_prompt:
            prompt = data.custom_prompt
        elif data.analysis_type == "invoice":
            prompt = DEFAULT_PROMPTS.get("invoice", "")
        elif data.analysis_type == "describe":
            prompt = DEFAULT_PROMPTS.get("describe", "")
        else:
            prompt = DEFAULT_PROMPTS.get("describe", "")
        
        base_name = Path(data.filename).stem
        
        # 调用现有的图片处理函数
        out_path, analysis_result = process_single_image(
            temp_path, prompt, DEFAULT_MODEL_PATH, 1024, 0.0, base_name
        )
        
        result = {
            "success": True,
            "tool": "analyze_image",
            "input": data.filename,
            "output": analysis_result,
            "analysis_type": data.analysis_type,
            "file_output": f"/outputs/{Path(out_path).name}",
            "message": f"图片 '{data.filename}' 分析完成"
        }
        
        return result
    
    finally:
        # 清理临时文件
        temp_path.unlink(missing_ok=True)

async def handle_structured_extraction(data: StructuredDataRequest) -> Dict[str, Any]:
    """处理结构化数据提取"""
    import tempfile
    import uuid
    import base64
    from pathlib import Path
    
    # 根据提取目标选择提示词
    target_prompts = {
        "invoice": "请提取该发票的所有关键信息，包含：发票号码、开票日期、销售方、购买方、商品/服务明细、总金额、税额等",
        "form": "请提取该表单的所有字段信息，保持结构层次",
        "contract": "请提取该合同的关键条款信息，包含：合同双方、主要条款、期限、金额等",
        "receipt": "请提取该收据/小票的所有信息，包含：商家、时间、商品、金额等"
    }
    
    prompt = target_prompts.get(data.extraction_target, "请从该文档中提取结构化信息")
    
    # 解码文件
    file_bytes = base64.b64decode(data.file_data)
    temp_path = UPLOAD_DIR / f"mcp_temp_{uuid.uuid4().hex}_{data.filename}"
    temp_path.write_bytes(file_bytes)
    
    try:
        base_name = Path(data.filename).stem
        
        # 判断文件类型并处理
        suffix = Path(data.filename).suffix.lower()
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
            "tool": "extract_structured_data",
            "input": data.filename,
            "extraction_target": data.extraction_target,
            "output": content,
            "file_output": f"/outputs/{Path(out_path).name}",
            "message": f"文档 {data.filename} 的结构化数据提取完成"
        }
        
        return result
    
    finally:
        temp_path.unlink(missing_ok=True)

async def handle_batch_process(data: BatchProcessRequest) -> Dict[str, Any]:
    """处理批量文档处理"""
    import tempfile
    import uuid
    from pathlib import Path
    
    processed_results = []
    
    for doc in data.documents:
        file_data = doc["file_data"]
        filename = doc["filename"]
        
        # 解码文件
        file_bytes = base64.b64decode(file_data)
        temp_path = UPLOAD_DIR / f"mcp_batch_{uuid.uuid4().hex}_{filename}"
        temp_path.write_bytes(file_bytes)
        
        try:
            base_name = Path(filename).stem
            suffix = Path(filename).suffix.lower()
            
            # 处理文档
            if suffix == ".pdf":
                out_path, content = process_pdf_with_progress(
                    temp_path, data.prompt, DEFAULT_MODEL_PATH, 1024, 0.0, base_name
                )
            else:
                out_path, content = process_single_image(
                    temp_path, data.prompt, DEFAULT_MODEL_PATH, 1024, 0.0, base_name
                )
            
            processed_results.append({
                "filename": filename,
                "output": content,
                "file_output": f"/outputs/{Path(out_path).name}"
            })
            
        finally:
            temp_path.unlink(missing_ok=True)
    
    # 如果要求合并结果
    if data.merge_results and processed_results:
        from datetime import datetime
        merged_content = ["# 批量处理结果合并\\n\\n"]
        
        for idx, result in enumerate(processed_results, 1):
            merged_content.append(f"## {idx}. {result['filename']}\\n\\n")
            merged_content.append(result['output'])
            merged_content.append("\\n\\n---\\n\\n")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        merged_filename = f"batch_merged_{timestamp}"
        merged_path = save_markdown("".join(merged_content), merged_filename)
        
        result = {
            "success": True,
            "tool": "batch_process_documents",
            "batch_size": len(data.documents),
            "results": processed_results,
            "merged": True,
            "merged_output": f"/outputs/{Path(merged_path).name}",
            "message": f"批量处理完成：处理了 {len(data.documents)} 个文档"
        }
    else:
        result = {
            "success": True,
            "tool": "batch_process_documents",
            "batch_size": len(data.documents),
            "results": processed_results,
            "merged": False,
            "message": f"批量处理完成：处理了 {len(data.documents)} 个文档"
        }
    
    return result

# API端点
@app.get("/")
async def root():
    """MCP HTTP API 根路径"""
    return {
        "service": "Vision AI MCP HTTP API",
        "version": "1.0.0",
        "tools": [
            "document_ocr",
            "analyze_image", 
            "extract_structured_data",
            "batch_process_documents"
        ],
        "endpoints": {
            "document_ocr": "/mcp/document_ocr",
            "analyze_image": "/mcp/analyze_image",
            "extract_structured_data": "/mcp/extract_structured_data",
            "batch_process": "/mcp/batch_process",
            "generic_tool": "/mcp/tool"
        }
    }

@app.get("/mcp/tools")
async def list_tools():
    """列出可用的MCP工具"""
    return {
        "tools": [
            {
                "name": "document_ocr",
                "description": "PDF文档OCR识别，将PDF转换为可编辑文本",
                "endpoint": "/mcp/document_ocr"
            },
            {
                "name": "analyze_image", 
                "description": "图片内容分析，描述图片内容和视觉元素",
                "endpoint": "/mcp/analyze_image"
            },
            {
                "name": "extract_structured_data",
                "description": "结构化数据提取，从发票、表单、合同等文档提取特定信息",
                "endpoint": "/mcp/extract_structured_data"
            },
            {
                "name": "batch_process_documents",
                "description": "批量文档处理，支持多个文档同时处理并合并结果",
                "endpoint": "/mcp/batch_process"
            }
        ]
    }

@app.post("/mcp/document_ocr")
async def mcp_document_ocr(request: DocumentOCRRequest):
    """PDF文档OCR识别HTTP端点"""
    try:
        result = await handle_document_ocr(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCP工具调用失败: {str(e)}")

@app.post("/mcp/analyze_image")
async def mcp_analyze_image(request: ImageAnalysisRequest):
    """图片内容分析HTTP端点"""
    try:
        result = await handle_image_analysis(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCP工具调用失败: {str(e)}")

@app.post("/mcp/extract_structured_data")
async def mcp_extract_structured_data(request: StructuredDataRequest):
    """结构化数据提取HTTP端点"""
    try:
        result = await handle_structured_extraction(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCP工具调用失败: {str(e)}")

@app.post("/mcp/batch_process")
async def mcp_batch_process(request: BatchProcessRequest):
    """批量文档处理HTTP端点"""
    try:
        result = await handle_batch_process(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCP工具调用失败: {str(e)}")

@app.post("/mcp/tool")
async def mcp_generic_tool(request: MCPToolRequest):
    """通用MCP工具调用端点"""
    try:
        if request.name == "document_ocr":
            doc_data = DocumentOCRRequest(**request.arguments)
            result = await handle_document_ocr(doc_data)
        elif request.name == "analyze_image":
            img_data = ImageAnalysisRequest(**request.arguments)
            result = await handle_image_analysis(img_data)
        elif request.name == "extract_structured_data":
            ext_data = StructuredDataRequest(**request.arguments)
            result = await handle_structured_extraction(ext_data)
        elif request.name == "batch_process_documents":
            batch_data = BatchProcessRequest(**request.arguments)
            result = await handle_batch_process(batch_data)
        else:
            raise HTTPException(status_code=400, detail=f"未知的工具: {request.name}")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"工具调用失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
