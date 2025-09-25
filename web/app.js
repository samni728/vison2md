const fileInput = document.getElementById("file_input");
const dropzone = document.getElementById("dropzone");
const fileList = document.getElementById("file_list");
const startBtn = document.getElementById("start_btn");
const resultsDiv = document.getElementById("results");

// 模型配置元素
const modelTypeEl = document.getElementById("model_type");
const localModelConfigEl = document.getElementById("local_model_config");
const apiModelConfigEl = document.getElementById("api_model_config");
const modelPathEl = document.getElementById("model_path");
const baseUrlEl = document.getElementById("base_url");
const apiKeyEl = document.getElementById("api_key");
const modelNameEl = document.getElementById("model_name");

// 提示词配置元素
const promptTypeEl = document.getElementById("prompt_type");
const customPromptConfigEl = document.getElementById("custom_prompt_config");
const customPromptEl = document.getElementById("custom_prompt");
const promptPreviewEl = document.getElementById("prompt_preview_content");

// 其他参数
const maxTokensEl = document.getElementById("max_tokens");
const temperatureEl = document.getElementById("temperature");
const maxPagesEl = document.getElementById("max_pages");
const batchSizeEl = document.getElementById("batch_size");

// 处理配置容器
const pdfProcessingConfigEl = document.getElementById("pdf_processing_config");
const imageBatchConfigEl = document.getElementById("image_batch_config");

// 配置保存按钮
const saveLocalModelBtn = document.getElementById("save_local_model_btn");
const saveModelBtn = document.getElementById("save_model_btn");
const savePromptBtn = document.getElementById("save_prompt_btn");

// 配置管理容器
const savedModelsEl = document.getElementById("saved_models");
const savedPromptsEl = document.getElementById("saved_prompts");

let pendingFiles = [];
let defaultPrompts = {};
let savedConfigs = {};
let currentFileTypes = new Set(); // 跟踪当前选择的文件类型

// 初始化
async function init() {
  await loadDefaultPrompts();
  await loadSavedConfigs();
  setupEventListeners();
  updateModelConfigVisibility();
  updatePromptConfigVisibility();
  updatePromptPreview();
  renderSavedConfigs();
  updateProcessingConfigVisibility();

  // 初始化折叠状态（全部折叠）
  initCollapsibleSections();

  // 加载历史记录
  await refreshHistory();
}

// 加载默认提示词
async function loadDefaultPrompts() {
  try {
    const response = await fetch("/api/prompts");
    const data = await response.json();
    if (data.ok) {
      defaultPrompts = data.prompts;
    }
  } catch (error) {
    console.error("加载默认提示词失败:", error);
  }
}

// 加载保存的配置
async function loadSavedConfigs() {
  try {
    const response = await fetch("/api/saved-configs");
    const data = await response.json();
    if (data.ok) {
      savedConfigs = data.configs;
    }
  } catch (error) {
    console.error("加载保存的配置失败:", error);
  }
}

// 保存模型配置
async function saveModelConfig(modelType) {
  const name = prompt(`请输入配置名称:`);
  if (!name) return;

  const formData = new FormData();
  formData.append("config_type", "model");
  formData.append("name", name);
  formData.append("model_type", modelType);

  if (modelType === "local") {
    formData.append("model_path", modelPathEl.value);
  } else {
    formData.append("base_url", baseUrlEl.value);
    formData.append("api_key", apiKeyEl.value);
    formData.append("model_name", modelNameEl.value);
  }

  try {
    const response = await fetch("/api/save-config", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (data.ok) {
      alert("配置保存成功！");
      await loadSavedConfigs();
      renderSavedConfigs();
    } else {
      alert("保存失败: " + data.detail);
    }
  } catch (error) {
    alert("保存失败: " + error.message);
  }
}

// 保存自定义提示词
async function saveCustomPrompt() {
  const name = prompt(`请输入提示词名称:`);
  if (!name) return;

  const formData = new FormData();
  formData.append("config_type", "prompt");
  formData.append("name", name);
  formData.append("prompt_content", customPromptEl.value);

  try {
    const response = await fetch("/api/save-config", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (data.ok) {
      alert("提示词保存成功！");
      await loadSavedConfigs();
      renderSavedConfigs();
    } else {
      alert("保存失败: " + data.detail);
    }
  } catch (error) {
    alert("保存失败: " + error.message);
  }
}

// 加载模型配置
function loadModelConfig(config) {
  if (config.model_type === "local") {
    modelTypeEl.value = "local";
    modelPathEl.value = config.model_path;
  } else {
    modelTypeEl.value = "api";
    baseUrlEl.value = config.base_url;
    apiKeyEl.value = config.api_key;
    modelNameEl.value = config.model_name;
  }
  updateModelConfigVisibility();
}

// 加载自定义提示词
function loadCustomPrompt(config) {
  promptTypeEl.value = "custom";
  customPromptEl.value = config.content;
  updatePromptConfigVisibility();
  updatePromptPreview();
}

// 删除配置
async function deleteConfig(configType, configId) {
  if (!confirm("确定要删除这个配置吗？")) return;

  const formData = new FormData();
  formData.append("config_type", configType);
  formData.append("config_id", configId);

  try {
    const response = await fetch("/api/delete-config", {
      method: "DELETE",
      body: formData,
    });
    const data = await response.json();
    if (data.ok) {
      alert("配置删除成功！");
      await loadSavedConfigs();
      renderSavedConfigs();
    } else {
      alert("删除失败: " + data.detail);
    }
  } catch (error) {
    alert("删除失败: " + error.message);
  }
}

// 检测文件类型
function detectFileTypes(files) {
  const fileTypes = new Set();
  for (const file of files) {
    const extension = file.name.toLowerCase().split(".").pop();
    if (extension === "pdf") {
      fileTypes.add("pdf");
    } else if (
      ["jpg", "jpeg", "png", "webp", "bmp", "tiff"].includes(extension)
    ) {
      fileTypes.add("image");
    }
  }
  return fileTypes;
}

// 更新处理配置可见性
function updateProcessingConfigVisibility() {
  const hasPdf = currentFileTypes.has("pdf");
  const hasImage = currentFileTypes.has("image");

  // 显示PDF处理配置
  if (hasPdf) {
    pdfProcessingConfigEl.style.display = "block";
  } else {
    pdfProcessingConfigEl.style.display = "none";
  }

  // 显示图片批次处理配置
  if (hasImage) {
    imageBatchConfigEl.style.display = "block";
  } else {
    imageBatchConfigEl.style.display = "none";
  }
}

// 折叠功能
function toggleConfig(configId) {
  const content = document.getElementById(configId);
  const icon = document.getElementById(configId + "-icon");

  if (content.classList.contains("collapsed")) {
    // 展开
    content.classList.remove("collapsed");
    icon.textContent = "▼";
    icon.style.transform = "rotate(0deg)";
  } else {
    // 折叠
    content.classList.add("collapsed");
    icon.textContent = "▶";
    icon.style.transform = "rotate(0deg)";
  }
}

// 初始化折叠区域
function initCollapsibleSections() {
  // 模型配置默认折叠
  const modelConfigContent = document.getElementById("model-config");
  const modelConfigIcon = document.getElementById("model-config-icon");
  if (modelConfigContent) {
    modelConfigContent.classList.add("collapsed");
    if (modelConfigIcon) modelConfigIcon.textContent = "▶";
  }

  // 配置管理默认折叠
  const savedConfigsContent = document.getElementById("saved-configs");
  const savedConfigsIcon = document.getElementById("saved-configs-icon");
  if (savedConfigsContent) {
    savedConfigsContent.classList.add("collapsed");
    if (savedConfigsIcon) savedConfigsIcon.textContent = "▶";
  }

  // 提示词类型默认折叠
  const promptConfigContent = document.getElementById("prompt-config");
  const promptConfigIcon = document.getElementById("prompt-config-icon");
  if (promptConfigContent) {
    promptConfigContent.classList.add("collapsed");
    if (promptConfigIcon) promptConfigIcon.textContent = "▶";
  }
}

// 渲染保存的配置
function renderSavedConfigs() {
  // 渲染保存的模型配置
  savedModelsEl.innerHTML = "";
  if (savedConfigs.models && savedConfigs.models.length > 0) {
    savedConfigs.models.forEach((config) => {
      const configItem = document.createElement("div");
      configItem.className = "config-item";
      configItem.innerHTML = `
        <span class="config-name">${config.name}</span>
        <div class="config-actions">
          <button class="config-btn load-btn" onclick="loadModelConfig(${JSON.stringify(
            config
          ).replace(/"/g, "&quot;")})">加载</button>
          <button class="config-btn delete-btn" onclick="deleteConfig('model', '${
            config.id
          }')">删除</button>
        </div>
      `;
      savedModelsEl.appendChild(configItem);
    });
  } else {
    savedModelsEl.innerHTML =
      '<div class="config-empty">暂无保存的模型配置</div>';
  }

  // 渲染保存的自定义提示词
  savedPromptsEl.innerHTML = "";
  if (savedConfigs.prompts && savedConfigs.prompts.length > 0) {
    savedConfigs.prompts.forEach((config) => {
      const configItem = document.createElement("div");
      configItem.className = "config-item";
      configItem.innerHTML = `
        <span class="config-name">${config.name}</span>
        <div class="config-actions">
          <button class="config-btn load-btn" onclick="loadCustomPrompt(${JSON.stringify(
            config
          ).replace(/"/g, "&quot;")})">加载</button>
          <button class="config-btn delete-btn" onclick="deleteConfig('prompt', '${
            config.id
          }')">删除</button>
        </div>
      `;
      savedPromptsEl.appendChild(configItem);
    });
  } else {
    savedPromptsEl.innerHTML =
      '<div class="config-empty">暂无保存的自定义提示词</div>';
  }
}

// 设置事件监听器
function setupEventListeners() {
  modelTypeEl.addEventListener("change", updateModelConfigVisibility);
  promptTypeEl.addEventListener("change", updatePromptConfigVisibility);
  customPromptEl.addEventListener("input", updatePromptPreview);
  promptTypeEl.addEventListener("change", updatePromptPreview);

  // 保存按钮事件监听器
  saveLocalModelBtn.addEventListener("click", () => saveModelConfig("local"));
  saveModelBtn.addEventListener("click", () => saveModelConfig("api"));
  savePromptBtn.addEventListener("click", saveCustomPrompt);
}

// 更新模型配置可见性
function updateModelConfigVisibility() {
  const isLocal = modelTypeEl.value === "local";
  localModelConfigEl.style.display = isLocal ? "block" : "none";
  apiModelConfigEl.style.display = isLocal ? "none" : "block";
}

// 更新提示词配置可见性
function updatePromptConfigVisibility() {
  const isCustom = promptTypeEl.value === "custom";
  customPromptConfigEl.style.display = isCustom ? "block" : "none";
}

// 更新提示词预览
function updatePromptPreview() {
  const promptType = promptTypeEl.value;
  let previewText = "";

  if (promptType === "custom" && customPromptEl.value) {
    previewText = customPromptEl.value;
  } else if (promptType in defaultPrompts) {
    previewText = defaultPrompts[promptType];
  }

  promptPreviewEl.textContent = previewText || "请选择提示词类型";
}

function refreshList() {
  fileList.innerHTML = "";
  pendingFiles.forEach((f) => {
    const li = document.createElement("li");
    const left = document.createElement("div");
    left.className = "file-name";
    left.textContent = f.name;

    const right = document.createElement("div");
    right.className = "file-meta";
    right.textContent = `${Math.round(f.size / 1024)} KB`;

    li.appendChild(left);
    li.appendChild(right);
    fileList.appendChild(li);
  });
  startBtn.disabled = pendingFiles.length === 0;
}

function addFiles(files) {
  for (const f of files) {
    pendingFiles.push(f);
  }

  // 检测文件类型并更新UI
  currentFileTypes = detectFileTypes(pendingFiles);
  updateProcessingConfigVisibility();

  refreshList();
}

["dragenter", "dragover"].forEach((evt) => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.add("dragover");
  });
});
["dragleave", "drop"].forEach((evt) => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove("dragover");
  });
});

dropzone.addEventListener("drop", (e) => {
  const dt = e.dataTransfer;
  if (dt && dt.files) addFiles(dt.files);
});

fileInput.addEventListener("change", (e) => {
  addFiles(e.target.files);
  fileInput.value = "";
});

startBtn.addEventListener("click", async () => {
  if (pendingFiles.length === 0) return;
  startBtn.disabled = true;
  resultsDiv.innerHTML = "";

  // 创建进度条
  const progressContainer = document.createElement("div");
  progressContainer.className = "progress-container";
  progressContainer.innerHTML = `
    <div class="progress-header">
      <span id="progress-text">准备处理...</span>
      <span id="progress-percent">0%</span>
    </div>
    <div class="progress-bar">
      <div id="progress-fill" class="progress-fill"></div>
    </div>
  `;
  resultsDiv.appendChild(progressContainer);

  const progressText = document.getElementById("progress-text");
  const progressPercent = document.getElementById("progress-percent");
  const progressFill = document.getElementById("progress-fill");

  const form = new FormData();
  pendingFiles.forEach((f) => form.append("files", f));

  // 添加提示词配置
  form.append("prompt_type", promptTypeEl.value);
  if (promptTypeEl.value === "custom" && customPromptEl.value) {
    form.append("custom_prompt", customPromptEl.value);
  }

  // 添加模型配置
  if (modelTypeEl.value === "local") {
    if (modelPathEl.value) form.append("model_path", modelPathEl.value);
  } else {
    if (baseUrlEl.value) form.append("base_url", baseUrlEl.value);
    if (apiKeyEl.value) form.append("api_key", apiKeyEl.value);
    if (modelNameEl.value) form.append("model_name", modelNameEl.value);
  }

  // 添加其他参数
  if (maxTokensEl.value) form.append("max_tokens", maxTokensEl.value);
  if (temperatureEl.value) form.append("temperature", temperatureEl.value);
  if (maxPagesEl.value) form.append("max_pages", maxPagesEl.value);
  if (batchSizeEl.value) form.append("batch_size", batchSizeEl.value);

  try {
    // 显示处理中状态
    progressText.textContent = "正在处理文件...";
    progressFill.style.width = "50%";
    progressPercent.textContent = "50%";

    const resp = await fetch("/api/process", {
      method: "POST",
      body: form,
    });
    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`;
      try {
        const data = await resp.json();
        if (data?.detail) detail += `: ${data.detail}`;
      } catch {}
      throw new Error(detail);
    }

    const data = await resp.json();
    if (!data.ok) throw new Error("处理失败");

    // 更新进度
    progressText.textContent = "处理完成！";
    progressFill.style.width = "100%";
    progressPercent.textContent = "100%";

    // 显示结果
    data.results.forEach((r) => {
      const div = document.createElement("div");
      div.className = "result-item";
      const md = document.createElement("div");
      md.className = "md-preview";
      md.textContent = r.markdown || "";

      const originalLink = r.original_file_url
        ? ` | 原始文件：<a href="${r.original_file_url}" target="_blank">${r.original_file}</a>`
        : "";

      div.innerHTML = `
        <div><strong>${r.input}</strong> → <a href="${r.output_markdown}" target="_blank">${r.output_markdown}</a>${originalLink}</div>
        <div class="file-meta">已保存：${r.saved_path}</div>
      `;
      div.appendChild(md);
      resultsDiv.appendChild(div);
    });

    // 刷新历史
    await refreshHistory();
  } catch (err) {
    const div = document.createElement("div");
    div.className = "result-item error";
    div.textContent = "请求失败：" + (err?.message || err);
    resultsDiv.appendChild(div);
    progressText.textContent = "处理失败";
  } finally {
    startBtn.disabled = false;
    pendingFiles = [];
    refreshList();
    await refreshHistory(); // 刷新历史记录
  }
});

async function fetchHistory() {
  try {
    const resp = await fetch("/api/history");
    const data = await resp.json();
    if (data.ok) return Array.isArray(data.history) ? data.history : [];
  } catch (e) {
    console.error("加载历史失败", e);
  }
  return [];
}

async function deleteHistory(id) {
  try {
    const ok = confirm("确定删除该历史记录吗？");
    if (!ok) return;
    const url = "/api/history?record_id=" + encodeURIComponent(id);
    const resp = await fetch(url, { method: "DELETE" });
    const data = await resp.json();
    if (data.ok) {
      await refreshHistory();
    } else {
      alert("删除失败");
    }
  } catch (e) {
    alert("删除失败: " + e.message);
  }
}

async function refreshHistory() {
  const list = document.getElementById("history_list");
  if (!list) return;
  list.innerHTML = "";
  const items = await fetchHistory();
  if (items.length === 0) {
    const div = document.createElement("div");
    div.className = "result-item";
    div.textContent = "暂无历史记录";
    list.appendChild(div);
    return;
  }
  items
    .slice()
    .sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0))
    .forEach((h) => {
      const div = document.createElement("div");
      div.className = "result-item";
      const t = h.timestamp
        ? new Date(h.timestamp * 1000).toLocaleString()
        : "";
      div.innerHTML = `
        <div><strong>${
          h.input || ""
        }</strong> · <span style="color: var(--muted); font-size:12px;">${t}</span></div>
        <div>
          <a href="${h.output_markdown}" target="_blank">打开 Markdown</a>
          ${
            h.original_file_url
              ? ` | <a href="${h.original_file_url}" target="_blank">打开原始文件</a>`
              : ""
          }
          | <a href="#" data-id="${h.id}" class="history-delete">删除</a>
        </div>
      `;
      list.appendChild(div);
    });

  // 绑定删除事件
  list.querySelectorAll(".history-delete").forEach((a) => {
    a.addEventListener("click", async (e) => {
      e.preventDefault();
      const id = a.getAttribute("data-id");
      if (id) await deleteHistory(id);
    });
  });
}

// 初始化应用
init();
