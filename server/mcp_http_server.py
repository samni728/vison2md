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
        clean_output_text,
        load_saved_configs,
        CONFIG_FILE
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
        clean_output_text,
        load_saved_configs,
        CONFIG_FILE
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
    model_id: Optional[str] = None  # 指定使用哪个配置的模型

class ImageAnalysisRequest(BaseModel):
    file_data: str  # Base64编码的图片内容
    filename: str
    analysis_type: str = "describe"
    custom_prompt: Optional[str] = None
    model_id: Optional[str] = None  # 指定使用哪个配置的模型

class StructuredDataRequest(BaseModel):
    file_data: str  # Base64编码的文件内容
    filename: str
    extraction_target: str  # invoice, form, contract, receipt
    custom_schema: Optional[Dict] = None
    model_id: Optional[str] = None  # 指定使用哪个配置的模型

class BatchProcessRequest(BaseModel):
    documents: List[Dict[str, str]]  # [{"file_data": "...", "filename": "..."}]
    prompt: str
    merge_results: bool = False
    model_id: Optional[str] = None  # 指定使用哪个配置的模型

class MCPToolRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]

# 新增特定功能的请求模型
class ImageDescriptionRequest(BaseModel):
    file_data: str  # Base64编码的图片内容
    filename: str
    description_type: str = "describe"  # describe, detailed, structured
    custom_prompt: Optional[str] = None
    model_id: Optional[str] = None

class InvoiceExtractionRequest(BaseModel):
    file_data: str  # Base64编码的文件内容
    filename: str
    extraction_schema: Optional[Dict] = None  # 自定义提取字段
    model_id: Optional[str] = None

class BatchDocumentProcessingRequest(BaseModel):
    documents: List[Dict[str, str]]  # [{"file_data": "...", "filename": "..."}]
    process_type: str = "ocr"  # ocr, describe, extract
    merge_to_single: bool = True
    custom_prompt: Optional[str] = None
    model_id: Optional[str] = None

# 辅助函数：获取模型和提示配置
def get_model_and_prompt_by_id(model_id: Optional[str], default_prompt: str = ""):
    """根据模型ID获取对应的模型配置和提示"""
    configs = load_saved_configs()
    models = configs.get("models", [])
    prompts = configs.get("prompts", [])
    
    # 如果指定了模型ID，查找对应的模型
    selected_model = None
    if model_id:
        for model in models:
            if model.get("id") == model_id:
                selected_model = model
                break
    
    # 如果没有找到指定模型或没指定model_id，使用第一个API模型
    if not selected_model:
        for model in models:
            if model.get("model_type") == "api":
                selected_model = model
                break
    
    # 如果还是没有找到API模型，使用默认
    if not selected_model:
        return None, default_prompt
    
    # 返回模型配置和默认提示词
    return selected_model, default_prompt

def get_prompt_by_id_or_type(prompt_id: Optional[str], prompt_type: str, default_content: str):
    """根据提示ID或类型获取提示词配置"""
    configs = load_saved_configs()
    prompts = configs.get("prompts", [])
    
    # 如果指定了提示ID，查找对应的提示
    if prompt_id:
        for prompt in prompts:
            if prompt.get("id") == prompt_id:
                return prompt.get("content", default_content)
    
    # 如果没有指定或没找到，根据类型选择
    if prompt_type in ["describe", "invoice"]:
        for prompt in prompts:
            if prompt_type in prompt.get("name", "").lower() or prompt_type in prompt.get("content", "").lower():
                return prompt.get("content", default_content)
    
    return default_content

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
        # 获取模型配置
        selected_model, default_prompt = get_model_and_prompt_by_id(
            data.model_id, 
            DEFAULT_PROMPTS.get("pdf_extract", "")
        )
        
        # 确定要使用的提示词
        prompt = data.prompt or get_prompt_by_id_or_type(None, "pdf_extract", default_prompt)
        base_name = Path(data.filename).stem
        
        # 根据模型配置选择处理方式
        if selected_model and selected_model.get("model_type") == "api":
            # 使用API模型 - 动态构建模型配置
            model_config = "[api]"
            if "base_url" in selected_model:
                model_config += f"url={selected_model['base_url']}"
            if "api_key" in selected_model:
                model_config += f"&key={selected_model['api_key']}"
            if "model_name" in selected_model:
                model_config += f"&model={selected_model['model_name']}"
            
            out_path, md_content = process_pdf_with_progress(
                temp_path, prompt, model_config, 1024, 0.0, 
                base_name, data.max_pages
            )
        else:
            # 使用默认本地模型
            out_path, md_content = process_pdf_with_progress(
                temp_path, prompt, DEFAULT_MODEL_PATH, 1024, 0.0, 
                base_name, data.max_pages
            )
        
        model_info = selected_model.get("name", "默认模型") if selected_model else "默认模型"
        
        result = {
            "success": True,
            "tool": "document_ocr",
            "input": data.filename,
            "output": md_content,
            "model_used": model_info,
            "file_output": f"/outputs/{Path(out_path).name}",
            "message": f"PDF文档 '{data.filename}' 处理完成 (使用模型: {model_info})"
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
        # 获取模型配置
        selected_model, default_prompt = get_model_and_prompt_by_id(
            data.model_id, 
            DEFAULT_PROMPTS.get("describe", "")
        )
        
        # 确定要使用的提示词
        if data.analysis_type == "custom" and data.custom_prompt:
            prompt = data.custom_prompt
        elif data.analysis_type == "invoice":
            prompt = get_prompt_by_id_or_type(None, "invoice", DEFAULT_PROMPTS.get("invoice", ""))
        elif data.analysis_type == "describe":
            prompt = get_prompt_by_id_or_type(None, "describe", default_prompt)
        else:
            prompt = default_prompt
        
        base_name = Path(data.filename).stem
        
        # 根据模型配置选择处理方式
        if selected_model and selected_model.get("model_type") == "api":
            # 使用API模型 - 动态构建模型配置
            model_config = "[api]"
            if "base_url" in selected_model:
                model_config += f"url={selected_model['base_url']}"
            if "api_key" in selected_model:
                model_config += f"&key={selected_model['api_key']}"
            if "model_name" in selected_model:
                model_config += f"&model={selected_model['model_name']}"
            
            out_path, analysis_result = process_single_image(
                temp_path, prompt, model_config, 1024, 0.0, base_name
            )
        else:
            # 使用默认本地模型
            out_path, analysis_result = process_single_image(
                temp_path, prompt, DEFAULT_MODEL_PATH, 1024, 0.0, base_name
            )
        
        model_info = selected_model.get("name", "默认模型") if selected_model else "默认模型"
        
        result = {
            "success": True,
            "tool": "analyze_image",
            "input": data.filename,
            "output": analysis_result,
            "analysis_type": data.analysis_type,
            "model_used": model_info,
            "file_output": f"/outputs/{Path(out_path).name}",
            "message": f"图片 '{data.filename}' 分析完成 (使用模型: {model_info})"
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

# 新增：专门的PDF文档识别函数
async def handle_document_ocr_new(data: DocumentOCRRequest) -> Dict[str, Any]:
    """专门处理PDF文档OCR识别"""
    import tempfile
    import uuid
    import base64
    from pathlib import Path
    import fitz  # PyMuPDF
    
    # 解码base64文件内容
    file_bytes = base64.b64decode(data.file_data)
    
    # 保存临时文件
    temp_path = UPLOAD_DIR / f"mcp_ocr_{uuid.uuid4().hex}_{data.filename}"
    temp_path.write_bytes(file_bytes)
    
    try:
        selected_model, default_prompt = get_model_and_prompt_by_id(
            data.model_id, 
            DEFAULT_PROMPTS.get("pdf_extract", "")
        )
        
        prompt = data.prompt or get_prompt_by_id_or_type(None, "pdf_extract", default_prompt)
        base_name = Path(data.filename).stem
        
        if selected_model and selected_model.get("model_type") == "api":
            model_config = "[api]"
            if "base_url" in selected_model:
                model_config += f"url={selected_model['base_url']}"
            if "api_key" in selected_model:
                model_config += f"&key={selected_model['api_key']}"
            if "model_name" in selected_model:
                model_config += f"&model={selected_model['model_name']}"
            
            out_path, md_content = process_pdf_with_progress(
                temp_path, prompt, model_config, 1024, 0.0, 
                base_name, data.max_pages
            )
        else:
            out_path, md_content = process_pdf_with_progress(
                temp_path, prompt, DEFAULT_MODEL_PATH, 1024, 0.0, 
                base_name, data.max_pages
            )
        
        model_info = selected_model.get("name", "默认模型") if selected_model else "默认模型"
        
        result = {
            "success": True,
            "tool": "document_ocr",
            "input": data.filename,
            "output": md_content,
            "model_used": model_info,
            "file_output": f"/outputs/{Path(out_path).name}",
            "message": f"PDF文档 '{data.filename}' OCR识别完成 (使用模型: {model_info})"
        }
        
        return result
    
    finally:
        temp_path.unlink(missing_ok=True)

# 新增：专门处理图片内容描述
async def handle_image_description(data: ImageDescriptionRequest) -> Dict[str, Any]:
    """专门处理图片内容描述"""
    import tempfile
    import uuid
    import base64
    from pathlib import Path
    
    file_bytes = base64.b64decode(data.file_data)
    temp_path = UPLOAD_DIR / f"mcp_desc_{uuid.uuid4().hex}_{data.filename}"
    temp_path.write_bytes(file_bytes)
    
    try:
        selected_model, default_prompt = get_model_and_prompt_by_id(
            data.model_id, 
            DEFAULT_PROMPTS.get("describe", "")
        )
        
        # 根据描述类型确定提示词
        if data.custom_prompt:
            prompt = data.custom_prompt
        elif data.description_type == "detailed":
            prompt = get_prompt_by_id_or_type(None, "describe", 
                "请详细描述这张图片的内容，包括所有可见的文字、物体、场景、颜色、动作等。" + default_prompt)
        elif data.description_type == "structured":
            prompt = get_prompt_by_id_or_type(None, "structure", 
                """请按照以下结构化格式描述这张图片：
人物：[列出图片中的人物及其特征]
物体：[列出图片中的主要物体]
场景：[描述图片的场景和环境]
文字：[提取并描述图片中的文字内容]
颜色：[主色调和细节颜色]
情感：[图片传达的情感和氛围]""")
        else:  # describe
            prompt = default_prompt
        
        base_name = Path(data.filename).stem
        
        if selected_model and selected_model.get("model_type") == "api":
            model_config = "[api]"
            if "base_url" in selected_model:
                model_config += f"url={selected_model['base_url']}"
            if "api_key" in selected_model:
                model_config += f"&key={selected_model['api_key']}"
            if "model_name" in selected_model:
                model_config += f"&model={selected_model['model_name']}"
            
            out_path, description = process_single_image(
                temp_path, prompt, model_config, 1024, 0.0, base_name
            )
        else:
            out_path, description = process_single_image(
                temp_path, prompt, DEFAULT_MODEL_PATH, 1024, 0.0, base_name
            )
        
        model_info = selected_model.get("name", "默认模型") if selected_model else "默认模型"
        
        result = {
            "success": True,
            "tool": "image_description",
            "input": data.filename,
            "output": description,
            "description_type": data.description_type,
            "model_used": model_info,
            "file_output": f"/outputs/{Path(out_path).name}",
            "message": f"图片 '{data.filename}' 描述完成 (使用模型: {model_info})"
        }
        
        return result
    
    finally:
        temp_path.unlink(missing_ok=True)

# 新增：发票信息提取
async def handle_invoice_extraction(data: InvoiceExtractionRequest) -> Dict[str, Any]:
    """专门处理发票信息结构化提取"""
    import tempfile
    import uuid
    import base64
    from pathlib import Path
    
    file_bytes = base64.b64decode(data.file_data)
    temp_path = UPLOAD_DIR / f"mcp_invoice_{uuid.uuid4().hex}_{data.filename}"
    temp_path.write_bytes(file_bytes)
    
    try:
        selected_model, default_prompt = get_model_and_prompt_by_id(
            data.model_id, 
            DEFAULT_PROMPTS.get("invoice", "")
        )
        
        # 构建专门的发票提取提示词
        invoice_prompt = """请从这张发票/收据中提取以下信息，以JSON格式返回：

{
  "invoice_number": "发票号码",
  "date": "开票日期",
  "vendor": "开票方/销售方",
  "buyer": "购买方",
  "items": [
    {
      "description": "商品描述",
      "quantity": "数量",
      "unit_price": "单价",
      "subtotal": "小计"
    }
  ],
  "subtotal": "总计（不含税）",
  "tax": "税额",
  "total": "总额",
  "payment_method": "付款方式",
  "notes": "备注"
}

请严格按照JSON格式返回，确保数字单位为人民币元。"""
        
        if data.extraction_schema:
            schema_items = data.extraction_schema.get("items", [])
            if schema_items:
                invoice_prompt = invoice_prompt.replace("items", json.dumps(schema_items, ensure_ascii=False))
        
        if data.filename.lower().endswith('.pdf'):
            # 处理PDF发票
            base_name = Path(data.filename).stem
            
            if selected_model and selected_model.get("model_type") == "api":
                model_config = "[api]"
                if "base_url" in selected_model:
                    model_config += f"url={selected_model['base_url']}"
                if "api_key" in selected_model:
                    model_config += f"&key={selected_model['api_key']}"
                if "model_name" in selected_model:
                    model_config += f"&model={selected_model['model_name']}"
                
                out_path, extracted_data = process_pdf_with_progress(
                    temp_path, invoice_prompt, model_config, 1024, 0.0, 
                    base_name, 5  # 限制页数
                )
            else:
                out_path, extracted_data = process_pdf_with_progress(
                    temp_path, invoice_prompt, DEFAULT_MODEL_PATH, 1024, 0.0, 
                    base_name, 5
                )
        else:
            # 处理图片发票
            base_name = Path(data.filename).stem
            
            if selected_model and selected_model.get("model_type") == "api":
                model_config = "[api]"
                if "base_url" in selected_model:
                    model_config += f"url={selected_model['base_url']}"
                if "api_key" in selected_model:
                    model_config += f"&key={selected_model['api_key']}"
                if "model_name" in selected_model:
                    model_config += f"&model={selected_model['model_name']}"
                
                out_path, extracted_data = process_single_image(
                    temp_path, invoice_prompt, model_config, 1024, 0.0, base_name
                )
            else:
                out_path, extracted_data = process_single_image(
                    temp_path, invoice_prompt, DEFAULT_MODEL_PATH, 1024, 0.0, base_name
                )
        
        model_info = selected_model.get("name", "默认模型") if selected_model else "默认模型"
        
        result = {
            "success": True,
            "tool": "invoice_extraction",
            "input": data.filename,
            "extracted_data": extracted_data,
            "model_used": model_info,
            "file_output": f"/outputs/{Path(out_path).name}",
            "message": f"发票 '{data.filename}' 信息提取完成 (使用模型: {model_info})"
        }
        
        return result
    
    finally:
        temp_path.unlink(missing_ok=True)

# 新增：批量文档转统一文档
async def handle_batch_document_processing(data: BatchDocumentProcessingRequest) -> Dict[str, Any]:
    """专门处理批量文档合并为统一文档"""
    import tempfile
    import uuid
    import base64
    from pathlib import Path
    
    if not data.documents:
        return {"success": False, "error": "没有提供任何文档"}
    
    try:
        processed_results = []
        temp_paths = []
        
        # 处理每个文档
        for i, doc in enumerate(data.documents):
            file_bytes = base64.b64decode(doc["file_data"])
            filename = doc["filename"]
            
            temp_path = UPLOAD_DIR / f"mcp_batch_{uuid.uuid4().hex}_{filename}"
            temp_path.write_bytes(file_bytes)
            temp_paths.append(temp_path)
            
            try:
                selected_model, default_prompt = get_model_and_prompt_by_id(
                    data.model_id, 
                    DEFAULT_PROMPTS.get("document_ocr", "")
                )
                
                if data.process_type == "ocr":
                    prompt = data.custom_prompt or get_prompt_by_id_or_type(None, "pdf_extract", default_prompt)
                elif data.process_type == "describe":
                    prompt = data.custom_prompt or get_prompt_by_id_or_type(None, "describe", 
                        "请详细描述这个图片/文档的内容。")
                else:  # extract
                    prompt = data.custom_prompt or get_prompt_by_id_or_type(None, "invoice", 
                        "请从文档中提取重要信息，包括标题、主要内容、关键数据等。")
                
                base_name = Path(filename).stem
                
                if selected_model and selected_model.get("model_type") == "api":
                    model_config = "[api]"
                    if "base_url" in selected_model:
                        model_config += f"url={selected_model['base_url']}"
                    if "api_key" in selected_model:
                        model_config += f"&key={selected_model['api_key']}"
                    if "model_name" in selected_model:
                        model_config += f"&model={selected_model['model_name']}"
                    
                    if filename.lower().endswith('.pdf'):
                        out_path, content = process_pdf_with_progress(
                            temp_path, prompt, model_config, 1024, 0.0, 
                            base_name, 10
                        )
                    else:
                        out_path, content = process_single_image(
                            temp_path, prompt, model_config, 1024, 0.0, base_name
                        )
                else:
                    if filename.lower().endswith('.pdf'):
                        out_path, content = process_pdf_with_progress(
                            temp_path, prompt, DEFAULT_MODEL_PATH, 1024, 0.0, 
                            base_name, 10
                        )
                    else:
                        out_path, content = process_single_image(
                            temp_path, prompt, DEFAULT_MODEL_PATH, 1024, 0.0, base_name
                        )
                
                processed_results.append({
                    "filename": filename,
                    "content": content,
                    "output_path": f"/outputs/{Path(out_path).name}"
                })
                
            except Exception as e:
                processed_results.append({
                    "filename": filename,
                    "error": f"处理失败: {str(e)}"
                })
        
        # 合并为统一文档
        if data.merge_to_single and processed_results:
            merged_content = []
            merged_content.append("# 合并文档处理结果\n")
            merged_content.append(f"**处理时间: {Path().cwd()}**\n")
            merged_content.append(f"**文档数量: {len(data.documents)}**\n\n")
            
            for i, result in enumerate(processed_results, 1):
                if "error" in result:
                    merged_content.append(f"## 文档 {i}: {result['filename']}\n")
                    merged_content.append(f"**处理失败**: {result['error']}\n\n")
                else:
                    merged_content.append(f"## 文档 {i}: {result['filename']}\n")
                    merged_content.append("---\n\n")
                    merged_content.append(result['content'])
                    merged_content.append("\n\n")
            
            # 保存合并文档
            merged_filename = f"batch_merged_{uuid.uuid4().hex[:8]}.md"
            merged_path = save_markdown("".join(merged_content), merged_filename)
            
            result = {
                "success": True,
                "tool": "batch_document_processing",
                "input_count": len(data.documents),
                "processed_count": len([r for r in processed_results if "error" not in r]),
                "results": processed_results,
                "merged_to_single": True,
                "merged_output": f"/outputs/{Path(merged_path).name}",
                "message": f"批量文档处理并合并完成，共处理 {len(data.documents)} 个文档"
            }
        else:
            result = {
                "success": True,
                "tool": "batch_document_processing",
                "input_count": len(data.documents),
                "processed_count": len([r for r in processed_results if "error" not in r]),
                "results": processed_results,
                "merged_to_single": False,
                "message": f"批量文档处理完成，共处理 {len(data.documents)} 个文档"
            }
        
        return result
    
    finally:
        # 清理临时文件
        for temp_path in temp_paths:
            temp_path.unlink(missing_ok=True)

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
            "batch_process_documents",
            "pdf_document_ocr",
            "image_description",
            "invoice_extraction",
            "batch_unified_document"
        ],
        "endpoints": {
            "document_ocr": "/mcp/document_ocr",
            "analyze_image": "/mcp/analyze_image",
            "extract_structured_data": "/mcp/extract_structured_data",
            "batch_process": "/mcp/batch_process",
            "pdf_document_ocr": "/mcp/pdf_ocr",
            "image_description": "/mcp/image_description",
            "invoice_extraction": "/mcp/invoice_extraction",
            "batch_unified_document": "/mcp/batch_unified",
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
            },
            {
                "name": "pdf_document_ocr",
                "description": "专门的PDF文档OCR识别功能",
                "endpoint": "/mcp/pdf_ocr"
            },
            {
                "name": "image_description",
                "description": "图片内容详细描述和结构化分析",
                "endpoint": "/mcp/image_description"
            },
            {
                "name": "invoice_extraction",
                "description": "发票信息结构化提取",
                "endpoint": "/mcp/invoice_extraction"
            },
            {
                "name": "batch_unified_document",
                "description": "批量文档和图片转统一文档",
                "endpoint": "/mcp/batch_unified"
            }
        ]
    }

@app.get("/mcp/models")
async def list_configured_models():
    """列出已配置的模型"""
    configs = load_saved_configs()
    models = configs.get("models", [])
    
    # 过滤出有用的模型信息
    model_list = []
    for model in models:
        model_info = {
            "id": model.get("id", ""),
            "name": model.get("name", ""),
            "model_type": model.get("model_type", ""),
            "model_name": model.get("model_name", ""),
            "base_url": model.get("base_url", ""),
        }
        model_list.append(model_info)
    
    return {
        "models": model_list,
        "default_model": models[0].get("id", "") if models else None
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

# 新增专门功能端点

@app.post("/mcp/pdf_ocr")
async def mcp_pdf_ocr(request: DocumentOCRRequest):
    """专门的PDF文档OCR识别端点"""
    try:
        result = await handle_document_ocr_new(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF OCR处理失败: {str(e)}")

@app.post("/mcp/image_description")
async def mcp_image_description(request: ImageDescriptionRequest):
    """专门的图片内容描述端点"""
    try:
        result = await handle_image_description(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片描述处理失败: {str(e)}")

@app.post("/mcp/invoice_extraction")
async def mcp_invoice_extraction(request: InvoiceExtractionRequest):
    """专门的发票信息提取端点"""
    try:
        result = await handle_invoice_extraction(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发票提取失败: {str(e)}")

@app.post("/mcp/batch_unified")
async def mcp_batch_unified_document(request: BatchDocumentProcessingRequest):
    """批量文档或图片转统一文档端点"""
    try:
        result = await handle_batch_document_processing(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量文档合并失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
