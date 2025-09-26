import os
import shutil
import tempfile
import uuid
import subprocess
import re
import base64
import requests
import json
from pathlib import Path
from typing import List, Tuple, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    fitz = None
    PYMUPDF_AVAILABLE = False

APP_ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = APP_ROOT / "uploads"
OUTPUT_DIR = APP_ROOT / "outputs"
WEB_DIR = APP_ROOT / "web"
CONFIG_FILE = APP_ROOT / "saved_configs.json"
HISTORY_FILE = APP_ROOT / "history.json"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
WEB_DIR.mkdir(parents=True, exist_ok=True)

# 历史记录存取
def load_history() -> List[dict]:
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception:
        return []

def save_history(history: List[dict]):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存历史记录失败: {str(e)}")

DEFAULT_MODEL_PATH = str(Path.home() / ".cache/lm-studio/models/EZCon/Qwen2.5-VL-7B-Instruct-4bit-mlx")

# 默认提示词选项
DEFAULT_PROMPTS = {
    "describe": "请详细描述这张图片的内容，包括图片中的主要元素、颜色、布局等。",
    "invoice": "请用 markdown 格式详细描述这张发票或文档页面的信息，包括但不限于：发票号码、日期、金额、商家信息、商品明细等。",
    "pdf_extract": """请仔细识别并提取这个PDF页面的所有文本内容，按照以下要求进行：

1. **保持原文格式**：严格按照原文档的段落结构、标题层级、列表格式等进行排版
2. **完整提取**：提取页面上的所有文字内容，包括标题、正文、图表说明、页眉页脚等
3. **保持排版**：使用适当的Markdown格式（标题、列表、表格等）来重现原文档的视觉效果
4. **序号保留**：保持原有的编号、项目符号、引用格式等
5. **表格处理**：如果是表格，请用Markdown表格格式呈现
6. **公式处理**：如果是数学公式或特殊符号，请尽量保持原样或使用适当的Markdown语法

请直接输出提取的内容，不要添加任何说明文字或解释。""",
    "custom": "请用 markdown 格式详细描述这张发票或文档页面的信息。"
}

DEFAULT_PROMPT = DEFAULT_PROMPTS["invoice"]

app = FastAPI(title="Qwen2.5-VL WebUI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def run_mlx_vlm_generate(image_path: Path, prompt: str, model_path: str, max_tokens: int, temperature: float) -> str:
    python_exec = os.environ.get("VLM_PYTHON", "python")
    
    # 使用MLX VLM支持的基本参数
    cmd = [
        python_exec, "-m", "mlx_vlm", "generate",
        "--model", model_path,
        "--max-tokens", str(max_tokens),
        "--temperature", str(temperature),
        "--prompt", prompt,
        "--image", str(image_path),
    ]
    
    try:
        # 设置环境变量以优化内存使用
        env = os.environ.copy()
        env["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"  # 减少内存预留
        
        completed = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True,
            env=env,
            timeout=300  # 5分钟超时
        )
        stdout = (completed.stdout or "").strip()
        if not stdout:
            stdout = (completed.stderr or "").strip()
        return stdout
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="模型调用超时，可能是内存不足导致的")
    except subprocess.CalledProcessError as e:
        stderr = (e.stdout or "") + "\n" + (e.stderr or "")
        if "Insufficient Memory" in stderr or "OutOfMemory" in stderr:
            raise HTTPException(status_code=500, detail=f"内存不足，请尝试减少PDF页数或使用API调用\n错误: {stderr.strip()}")
        else:
            raise HTTPException(status_code=500, detail=f"模型调用失败\n命令: {' '.join(cmd)}\n错误: {stderr.strip()}")


def run_api_generate(image_path: Path, prompt: str, base_url: str, api_key: str, model_name: str, max_tokens: int, temperature: float) -> str:
    """通过API调用生成内容"""
    try:
        # 读取图片并转换为base64
        with open(image_path, "rb") as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        
        # 构建请求数据
        data = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 发送请求
        response = requests.post(
            base_url,
            json=data,
            headers=headers,
            timeout=120
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500, 
                detail=f"API调用失败: HTTP {response.status_code} - {response.text}"
            )
        
        result = response.json()
        
        # 提取生成的内容
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            return content
        else:
            raise HTTPException(status_code=500, detail="API响应格式错误")
            
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API请求失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API调用出错: {str(e)}")


def load_saved_configs() -> dict:
    """加载保存的配置"""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"models": [], "prompts": []}
    except Exception:
        return {"models": [], "prompts": []}

def save_configs(configs: dict):
    """保存配置到文件 - Docker容器兼容版本"""
    import os
    import tempfile
    import shutil
    import time
    
    max_retries = 3
    retry_delay = 0.5  # seconds
    
    for attempt in range(max_retries):
        try:
            # 确保目录存在
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # 生成配置内容
            config_content = json.dumps(configs, ensure_ascii=False, indent=2)
            
            # 方法1：直接写入（最快最简单）
            try:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    f.write(config_content)
                    f.flush()
                    os.fsync(f.fileno())
                
                # 验证写入成功
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    if loaded_data == configs:  # 验证数据一致性
                        return  # 成功了
                    else:
                        raise Exception("数据验证失败")
                        
            except (OSError, IOError) as e:
                if "Device or resource busy" in str(e):
                    if attempt >= max_retries - 1:
                        raise Exception("文件被持续锁定，需要检查其他进程是否在访问配置文件")
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    raise e
            
            except:
                # 文件验证失败，用临时文件方法
                pass
            
            # 方法2：临时文件原子性替换（用于解决并发和锁定问题）
            import tempfile
            with tempfile.NamedTemporaryFile(
                mode='w+', 
                encoding='utf-8', 
                suffix='.tmp',
                dir='/tmp',  # 在系统临时目录，避免Docker文件锁定
                delete=False
            ) as tmp_file:
                tmp_file.write(config_content)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
                temp_name = tmp_file.name
            
            # 用shell mv实现原子性替换
            import subprocess
            try:
                subprocess.run(['mv', temp_name, str(CONFIG_FILE)], 
                             check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # 如果mv不可用，使用python shutil
                shutil.move(temp_name, CONFIG_FILE)
            
            # 最终验证文件写入
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                if json.load(f) == configs:
                    return
                else:
                    raise Exception("文件验证失败")
                    
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                # 用户友好的错误提示
                error_msg = str(e)
                if "Device or resource busy" in error_msg:
                    error_msg = "配置被锁定 - 请等待其他操作完成后再试"
                elif "Permission denied" in error_msg:
                    error_msg = "权限不足 - 检查Docker文件挂载权限"
                elif "read-only" in error_msg.lower():
                    error_msg = "配置目录只读 - 检查Docker卷权限设置"
                    
                raise HTTPException(status_code=500, detail=f"无法保存配置: {error_msg}")

def clean_output_text(raw: str) -> str:
    # 首先移除思考过程内容（<think>标签内的所有内容）
    # 处理完整的think标签
    text = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL | re.IGNORECASE)
    # 处理不完整的think标签（没有结束标签的情况）
    text = re.sub(r'<think>.*$', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 去除常见噪声（Prompt/统计/分隔符等）
    lines = text.splitlines()
    cleaned: List[str] = []
    skip_next = False
    
    for i, line in enumerate(lines):
        L = line.strip()
        
        # 跳过空行
        if not L:
            cleaned.append(line)
            continue
            
        # 跳过系统消息和特殊标记
        if (L == "==========" or
            L.startswith("Prompt:") or
            L.startswith("Generation:") or
            L.startswith("Peak memory:") or
            L.startswith("You are a helpful assistant") or
            L.startswith("<|im_start|>") or
            L.startswith("<|im_end|>") or
            L.startswith("<|vision_start|>") or
            L.startswith("<|vision_end|>") or
            L.startswith("<|image_pad|>") or
            L.startswith("Files:") or  # 移除文件路径信息
            "请识别 pdf" in L or  # 移除提示词内容
            "第" in L and "页的内容如下" in L):  # 移除页面说明
            continue
            
        # 跳过包含提示词的完整行
        if any(phrase in L for phrase in [
            "请识别 pdf", "根据 pdf", "原来的格式", "markdown 格式",
            "生成对应页数", "md 文档", "请注意，由于原文档内容较长"
        ]):
            continue
            
        # 移除代码块标记（如果不是真正的代码内容）
        if L.startswith("```markdown") or L.startswith("```"):
            # 检查是否是真正的代码块内容
            if i > 0 and "第" in lines[i-1] and "页的内容如下" in lines[i-1]:
                continue
            cleaned.append(line)
            continue
            
        # 移除文件路径和临时信息
        if ("/var/folders/" in L or 
            "/tmp/" in L or 
            "pdf_pages_" in L or
            ".png" in L and "Files:" in L):
            continue
            
        cleaned.append(line)
    
    # 压缩尾部多余空行
    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    
    # 移除开头的无用文本
    text = re.sub(r'^.*?```markdown\s*', '', text, flags=re.DOTALL)
    text = re.sub(r'^.*?第.*?页的内容如下：\s*', '', text, flags=re.DOTALL)
    
    return text


def save_markdown(md_text: str, base_name: str) -> Path:
    safe_name = base_name
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        safe_name = safe_name.replace(ch, '_')
    out_path = OUTPUT_DIR / f"{safe_name}.md"
    out_path.write_text(md_text, encoding="utf-8")
    return out_path


def process_single_image(image_path: Path, prompt: str, model_path: str, max_tokens: int, temperature: float, out_base_name: str, base_url: Optional[str] = None, api_key: Optional[str] = None, model_name: Optional[str] = None, original_file_url: Optional[str] = None) -> Tuple[Path, str]:
    if base_url and api_key and model_name:
        # 使用API调用
        md_raw = run_api_generate(image_path, prompt, base_url, api_key, model_name, max_tokens, temperature)
    else:
        # 使用本地MLX模型
        md_raw = run_mlx_vlm_generate(image_path, prompt, model_path, max_tokens, temperature)
    
    md_clean = clean_output_text(md_raw)
    if original_file_url:
        header = f"[原始文件]({original_file_url})\n\n"
        md_to_save = header + md_clean
    else:
        md_to_save = md_clean
    out_path = save_markdown(md_to_save, out_base_name)
    return out_path, md_to_save


def process_pdf_with_progress(pdf_path: Path, prompt: str, model_path: str, max_tokens: int, temperature: float, out_base_name: str, max_pages: int = 10, base_url: Optional[str] = None, api_key: Optional[str] = None, model_name: Optional[str] = None, progress_callback=None, original_file_url: Optional[str] = None) -> Tuple[Path, str]:
    if not PYMUPDF_AVAILABLE:
        raise HTTPException(status_code=500, detail="PyMuPDF未安装，无法处理PDF文件。请运行: pip install PyMuPDF")
    
    doc = fitz.open(pdf_path)
    tmp_dir = Path(tempfile.mkdtemp(prefix="pdf_pages_"))
    
    total_pdf_pages = len(doc)
    
    try:
        all_results: List[str] = []
        
        # 计算需要处理的批次数量
        if total_pdf_pages <= max_pages:
            # 如果总页数小于等于最大页数，一次性处理
            batches = [(0, total_pdf_pages)]
        else:
            # 如果总页数大于最大页数，分批处理
            batches = []
            for start in range(0, total_pdf_pages, max_pages):
                end = min(start + max_pages, total_pdf_pages)
                batches.append((start, end))
        
        for batch_idx, (start_page, end_page) in enumerate(batches):
            batch_results: List[str] = []
            
            # 添加批次标题
            if len(batches) > 1:
                batch_results.append(f"## 批次 {batch_idx + 1}/{len(batches)} (第 {start_page + 1}-{end_page} 页)\n")
            
            for page_index in range(start_page, end_page):
                # 更新进度
                if progress_callback:
                    progress = int((page_index / total_pdf_pages) * 100)
                    progress_callback(f"正在处理第 {page_index + 1}/{total_pdf_pages} 页", progress)
                page = doc.load_page(page_index)
                
                # 降低DPI以减少内存使用：从180降到120
                pix = page.get_pixmap(dpi=120)
                img_path = tmp_dir / f"page_{page_index + 1}.png"
                pix.save(str(img_path))
                
                # 释放页面内存
                pix = None
                page = None

                page_prompt = f"第 {page_index + 1} 页：\n\n" + prompt
                
                try:
                    if base_url and api_key and model_name:
                        # 使用API调用
                        md_raw = run_api_generate(img_path, page_prompt, base_url, api_key, model_name, max_tokens, temperature)
                    else:
                        # 使用本地MLX模型
                        md_raw = run_mlx_vlm_generate(img_path, page_prompt, model_path, max_tokens, temperature)
                    
                    md_clean = clean_output_text(md_raw)
                    batch_results.append(f"## 第 {page_index + 1} 页\n\n" + md_clean + "\n\n---\n")
                    
                    # 删除临时图片文件以释放磁盘空间
                    img_path.unlink(missing_ok=True)
                    
                except Exception as e:
                    error_msg = f"处理第 {page_index + 1} 页时出错: {str(e)}"
                    batch_results.append(f"## 第 {page_index + 1} 页\n\n❌ {error_msg}\n\n---\n")
                    img_path.unlink(missing_ok=True)
                    continue
            
            all_results.extend(batch_results)
            
            # 如果不是最后一个批次，添加分隔符
            if batch_idx < len(batches) - 1:
                all_results.append("\n---\n")

        # 添加处理摘要和分页结构
        header_link = f"[原始文件]({original_file_url})\n\n" if original_file_url else ""
        summary = header_link + f"# 文档解析：{pdf_path.name}\n\n"
        summary += f"**处理摘要**: 共 {total_pdf_pages} 页，分 {len(batches)} 个批次处理\n\n"
        
        # 添加目录结构
        summary += "## 📋 文档目录\n\n"
        for i in range(1, total_pdf_pages + 1):
            summary += f"- [第 {i} 页](#第-{i}-页)\n"
        summary += "\n---\n\n"
        
        merged_md = summary + "\n".join(all_results)
        out_path = save_markdown(merged_md, out_base_name)
        return out_path, merged_md
        
    finally:
        # 确保清理资源
        doc.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/api/process")
async def process_files(
    files: List[UploadFile] = File(..., description="支持多文件：PDF 或 图片"),
    prompt_type: str = Form("invoice", description="提示词类型: describe, invoice, custom"),
    custom_prompt: str = Form("", description="自定义提示词"),
    model_path: str = Form(DEFAULT_MODEL_PATH, description="MLX模型路径"),
    base_url: str = Form("", description="API基础URL"),
    api_key: str = Form("", description="API密钥"),
    model_name: str = Form("", description="API模型名称"),
    max_tokens: int = Form(1024),
    temperature: float = Form(0.0),
    max_pages: int = Form(10, description="PDF最大处理页数"),
    batch_size: int = Form(5, description="图片批次处理数量"),
    merge_output: bool = Form(False, description="是否合并所有输出到单个文档"),
):
    if not files:
        raise HTTPException(status_code=400, detail="未接收到文件")

    # 确定使用的提示词
    if prompt_type == "custom" and custom_prompt:
        final_prompt = custom_prompt
    elif prompt_type in DEFAULT_PROMPTS:
        final_prompt = DEFAULT_PROMPTS[prompt_type]
    else:
        final_prompt = DEFAULT_PROMPT

    # 确定使用API还是本地模型
    use_api = bool(base_url and api_key and model_name)
    
    # 分离PDF和图片文件
    pdf_files = []
    image_files = []
    
    for uf in files:
        suffix = Path(uf.filename).suffix.lower()
        if suffix == ".pdf":
            pdf_files.append(uf)
        elif suffix in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
            image_files.append(uf)
        else:
            raise HTTPException(status_code=415, detail=f"不支持的文件类型: {suffix}")
    
    results = []
    
    # 处理PDF文件（单个处理，内部可能分批）
    for uf in pdf_files:
        suffix = Path(uf.filename).suffix.lower()
        temp_name = f"{uuid.uuid4().hex}{suffix}"
        temp_path = UPLOAD_DIR / temp_name
        with temp_path.open("wb") as w:
            content = await uf.read()
            w.write(content)

        # 保存原始文件副本（以原始文件名持久化）
        original_saved_path = UPLOAD_DIR / uf.filename
        try:
            with original_saved_path.open("wb") as ow:
                ow.write(content)
        except Exception:
            original_saved_path = temp_path

        base_name = Path(uf.filename).stem

        try:
            out_path, md_clean = process_pdf_with_progress(
                temp_path, final_prompt, model_path, max_tokens, temperature, base_name, max_pages,
                base_url if use_api else None, api_key if use_api else None, model_name if use_api else None,
                None,
                original_file_url=f"/uploads/{Path(original_saved_path).name}"
            )
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass

        results.append({
            "input": uf.filename,
            "output_markdown": f"/outputs/{Path(out_path).name}",
            "saved_path": str(out_path),
            "markdown": md_clean,
            "original_file": uf.filename,
            "original_file_url": f"/uploads/{Path(original_saved_path).name}",
            "original_saved_path": str(original_saved_path),
        })

        # 写入历史记录
        history = load_history()
        history.append({
            "id": uuid.uuid4().hex,
            "input": uf.filename,
            "output_markdown": f"/outputs/{Path(out_path).name}",
            "original_file_url": f"/uploads/{Path(original_saved_path).name}",
            "timestamp": int(__import__('time').time())
        })
        save_history(history)
    
    # 处理图片文件（批次处理）
    if image_files:
        # 将图片分批处理
        image_batches = []
        for i in range(0, len(image_files), batch_size):
            batch = image_files[i:i + batch_size]
            image_batches.append(batch)
        
        for batch_idx, batch in enumerate(image_batches):
            batch_results = []
            
            for uf in batch:
                suffix = Path(uf.filename).suffix.lower()
                temp_name = f"{uuid.uuid4().hex}{suffix}"
                temp_path = UPLOAD_DIR / temp_name
                with temp_path.open("wb") as w:
                    content = await uf.read()
                    w.write(content)
                # 保存原始文件副本
                original_saved_path = UPLOAD_DIR / uf.filename
                try:
                    with original_saved_path.open("wb") as ow:
                        ow.write(content)
                except Exception:
                    original_saved_path = temp_path

                base_name = Path(uf.filename).stem

                try:
                    out_path, md_clean = process_single_image(
                        temp_path, final_prompt, model_path, max_tokens, temperature, base_name,
                        base_url if use_api else None, api_key if use_api else None, model_name if use_api else None,
                        original_file_url=f"/uploads/{Path(original_saved_path).name}"
                    )
                    
                    batch_results.append({
                        "input": uf.filename,
                        "output_markdown": f"/outputs/{Path(out_path).name}",
                        "saved_path": str(out_path),
                        "markdown": md_clean,
                        "original_file": uf.filename,
                        "original_file_url": f"/uploads/{Path(original_saved_path).name}",
                        "original_saved_path": str(original_saved_path),
                    })

                    # 写入历史记录
                    history = load_history()
                    history.append({
                        "id": uuid.uuid4().hex,
                        "input": uf.filename,
                        "output_markdown": f"/outputs/{Path(out_path).name}",
                        "original_file_url": f"/uploads/{Path(original_saved_path).name}",
                        "timestamp": int(__import__('time').time())
                    })
                    save_history(history)
                finally:
                    try:
                        temp_path.unlink(missing_ok=True)
                    except Exception:
                        pass
            
            # 如果有多个批次，添加批次标题
            if len(image_batches) > 1:
                for result in batch_results:
                    result["markdown"] = f"## 图片批次 {batch_idx + 1}/{len(image_batches)}\n\n{result['markdown']}"
            
            results.extend(batch_results)

    # 如果需要合并输出，创建单个合并文档
    if merge_output and results:
        merged_content = []
        merged_content.append("# 合并文档处理结果\n\n")
        merged_content.append(f"处理时间：{__import__('time').strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        merged_content.append(f"处理文档数量：{len(results)} 个\n\n")
        merged_content.append("---\n\n")
        
        # 为每个文档创建一个清晰的章节
        for idx, result in enumerate(results, 1):
            # 获取原始文件名（完整文件名）
            original_filename = result.get('original_file', f'document_{idx}')
            filename_with_ext = Path(original_filename).stem
            upload_url = result.get('original_file_url', '')
            
            # 添加文档分隔标题
            merged_content.append(f"# {idx}. {filename_with_ext}\n\n")
            
            # 添加原始文件信息
            if upload_url:
                merged_content.append(f"**原始文件：** [{original_filename}]({upload_url})\n\n")
            else:
                merged_content.append(f"**原始文件：** {original_filename}\n\n")
            
            # 添加处理结果
            content = result.get('markdown', '')
            if content:
                merged_content.append(content)
            
            # 添加文档间分隔
            if idx < len(results):  # 不要在最后一个文档后添加分隔
                merged_content.append("\n\n---\n\n")
        
        # 保存合并文档
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        merged_filename = f"合并文档_{timestamp}"
        merged_path = save_markdown("".join(merged_content), merged_filename)
        
        # 创建新的结果，包含合并信息
        merged_result = {
            "input": f"合并处理 ({len(results)}个文档)",
            "output_markdown": f"/outputs/{Path(merged_path).name}",
            "saved_path": str(merged_path),
            "markdown": "".join(merged_content),
            "original_file": f"合并文档_{timestamp}",
            "original_file_url": "",
            "merged_count": len(results),
            "merged_original_files": [r.get('original_file', '') for r in results]
        }
        
        results = [merged_result]

    return JSONResponse({"ok": True, "results": results})


@app.get("/api/prompts")
async def get_prompts():
    """获取可用的默认提示词"""
    return JSONResponse({
        "ok": True,
        "prompts": DEFAULT_PROMPTS
    })


@app.get("/api/saved-configs")
async def get_saved_configs():
    """获取保存的配置"""
    configs = load_saved_configs()
    return JSONResponse({
        "ok": True,
        "configs": configs
    })


@app.post("/api/save-config")
async def save_config(
    config_type: str = Form(..., description="配置类型: model 或 prompt"),
    name: str = Form(..., description="配置名称"),
    model_type: str = Form("", description="模型类型: local 或 api"),
    model_path: str = Form("", description="MLX模型路径"),
    base_url: str = Form("", description="API基础URL"),
    api_key: str = Form("", description="API密钥"),
    model_name: str = Form("", description="API模型名称"),
    prompt_content: str = Form("", description="自定义提示词内容")
):
    """保存配置"""
    configs = load_saved_configs()
    
    if config_type == "model":
        # 保存模型配置
        model_config = {
            "id": str(uuid.uuid4()),
            "name": name,
            "model_type": model_type,
            "model_path": model_path,
            "base_url": base_url,
            "api_key": api_key,
            "model_name": model_name,
            "created_at": str(Path().cwd())
        }
        configs["models"].append(model_config)
    elif config_type == "prompt":
        # 保存自定义提示词
        prompt_config = {
            "id": str(uuid.uuid4()),
            "name": name,
            "content": prompt_content,
            "created_at": str(Path().cwd())
        }
        configs["prompts"].append(prompt_config)
    else:
        raise HTTPException(status_code=400, detail="无效的配置类型")
    
    save_configs(configs)
    
    return JSONResponse({
        "ok": True,
        "message": "配置保存成功",
        "config_id": model_config.get("id") if config_type == "model" else prompt_config.get("id")
    })


@app.delete("/api/delete-config")
async def delete_config(
    config_type: str = Form(..., description="配置类型: model 或 prompt"),
    config_id: str = Form(..., description="配置ID")
):
    """删除配置"""
    configs = load_saved_configs()
    
    if config_type == "model":
        # 删除模型配置
        configs["models"] = [m for m in configs["models"] if m["id"] != config_id]
    elif config_type == "prompt":
        # 删除提示词配置
        configs["prompts"] = [p for p in configs["prompts"] if p["id"] != config_id]
    else:
        raise HTTPException(status_code=400, detail="无效的配置类型")
    
    save_configs(configs)
    
    return JSONResponse({
        "ok": True,
        "message": "配置删除成功"
    })


@app.post("/api/process_stream")
async def process_files_stream(
    files: List[UploadFile] = File(..., description="支持多文件：PDF 或 图片"),
    prompt_type: str = Form("invoice", description="提示词类型: describe, invoice, custom"),
    custom_prompt: str = Form("", description="自定义提示词"),
    model_path: str = Form(DEFAULT_MODEL_PATH, description="MLX模型路径"),
    base_url: str = Form("", description="API基础URL"),
    api_key: str = Form("", description="API密钥"),
    model_name: str = Form("", description="API模型名称"),
    max_tokens: int = Form(1024),
    temperature: float = Form(0.0),
    max_pages: int = Form(10, description="PDF最大处理页数"),
):
    """流式处理文件，支持进度更新"""
    if not files:
        raise HTTPException(status_code=400, detail="未接收到文件")

    # 确定使用的提示词
    if prompt_type == "custom" and custom_prompt:
        final_prompt = custom_prompt
    elif prompt_type in DEFAULT_PROMPTS:
        final_prompt = DEFAULT_PROMPTS[prompt_type]
    else:
        final_prompt = DEFAULT_PROMPT

    # 确定使用API还是本地模型
    use_api = bool(base_url and api_key and model_name)
    
    async def generate_progress():
        results = []
        for file_idx, uf in enumerate(files):
            # 发送文件开始处理的消息
            yield f"data: {json.dumps({'type': 'file_start', 'file': uf.filename, 'file_index': file_idx})}\n\n"
            
            suffix = Path(uf.filename).suffix.lower()
            temp_name = f"{uuid.uuid4().hex}{suffix}"
            temp_path = UPLOAD_DIR / temp_name
            
            # 先读取文件内容，然后写入临时文件
            content = await uf.read()
            with temp_path.open("wb") as w:
                w.write(content)

            base_name = Path(uf.filename).stem

            try:
                def progress_callback(message, progress):
                    # 这里可以发送进度更新，但由于是同步函数，暂时跳过
                    pass
                
                if suffix in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
                    out_path, md_clean = process_single_image(
                        temp_path, final_prompt, model_path, max_tokens, temperature, base_name,
                        base_url if use_api else None, api_key if use_api else None, model_name if use_api else None
                    )
                elif suffix == ".pdf":
                    out_path, md_clean = process_pdf_with_progress(
                        temp_path, final_prompt, model_path, max_tokens, temperature, base_name, max_pages,
                        base_url if use_api else None, api_key if use_api else None, model_name if use_api else None,
                        progress_callback
                    )
                else:
                    raise HTTPException(status_code=415, detail=f"不支持的文件类型: {suffix}")
                
                result = {
                    "input": uf.filename,
                    "output_markdown": f"/outputs/{Path(out_path).name}",
                    "saved_path": str(out_path),
                    "markdown": md_clean,
                }
                results.append(result)
                
                # 发送文件处理完成的消息
                yield f"data: {json.dumps({'type': 'file_complete', 'file': uf.filename, 'result': result})}\n\n"
                
            except Exception as e:
                error_result = {
                    "input": uf.filename,
                    "error": str(e)
                }
                results.append(error_result)
                yield f"data: {json.dumps({'type': 'file_error', 'file': uf.filename, 'error': str(e)})}\n\n"
            finally:
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    pass
        
        # 发送最终结果
        yield f"data: {json.dumps({'type': 'complete', 'results': results})}\n\n"
    
    return StreamingResponse(generate_progress(), media_type="text/plain")


# 历史记录接口
@app.get("/api/history")
async def get_history():
    return JSONResponse({
        "ok": True,
        "history": load_history()
    })


@app.delete("/api/history")
async def delete_history_record(record_id: str = Query(...)):
    history = load_history()
    new_history = [h for h in history if h.get("id") != record_id]
    save_history(new_history)
    return JSONResponse({"ok": True})


app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
