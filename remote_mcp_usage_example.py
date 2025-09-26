#!/usr/bin/env python3
"""
使用远程 MCP 服务的完整示例
地址: http://192.168.10.200:9000
"""

from remote_mcp_client import RemoteVisionAIClient
import os

# 配置选项

def example_1_direct_configuration():
    """直接配置方式"""
    print("📋 方式1：直接配置远程地址")
    print("-" * 40)
    
    # 直接指定远程地址
    client = RemoteVisionAIClient("http://192.168.10.200:9000")
    
    # 获取可用工具
    tools = client.get_available_tools()
    print(f"可用工具: {tools}")
    
    # 分析图片示例
    if os.path.exists("example.jpg"):
        result = client.analyze_image("example.jpg", analysis_type="describe")
        print(f"图片分析结果: {result}")
    
    return client

def example_2_environment_configuration():
    """环境变量配置方式"""
    print("\n📋 方式2：环境变量配置")
    print("-" * 40)
    
    # 通过环境变量设置
    mcp_url = os.getenv('VISION_AI_URL', 'http://192.168.10.200:9000')
    client = RemoteVisionAIClient(mcp_url)
    
    print(f"使用服务地址: {mcp_url}")
    
    return client

def example_3_config_file():
    """配置文件方式"""
    print("\n📋 方式3：从配置文件读取")
    print("-" * 40)
    
    import json
    
    # 读取配置文件
    config_file = "mcp_remote_config_template.json"
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        base_url = config.get('vision_ai_remote', {}).get('base_url', 'http://192.168.10.200:9000')
        client = RemoteVisionAIClient(base_url)
        
        print(f"从配置加载，使用地址: {base_url}")
    else:
        client = RemoteVisionAIClient("http://192.168.10.200:9000")
        print("配置文件不存在，使用默认地址")
    
    return client

def demonstrate_usage():
    """演示如何使用远程服务"""
    print("🌐 远程 MCP 服务使用演示")
    print("==================================================")
    print("验证服务地址: http://192.168.10.200:9000")
    print()
    
    # 测试连接
    try:
        client = RemoteVisionAIClient("http://192.168.10.200:9000")
        tools_info = client.get_available_tools()
        
        if "error" not in tools_info:
            print("✅ 远程服务连接正常")
            print(f"📊 服务状态: {len(tools_info.get('tools', []))} 工具可用")
        else:
            print(f"❌ 远程服务连接失败: {tools_info['error']}")
            return
            
        # 获取可用模型列表
        models_info = client.get_configured_models()
        if "error" not in models_info:
            models = models_info.get("models", [])
            print(f"🤖 可用模型: {len(models)} 个")
            for model in models[:3]:  # 只显示前3个
                print(f"   - {model.get('name', 'N/A')} ({model.get('model_type', 'N/A')})")
            
        else:
            print(f"⚠️ 无法获取模型列表: {models_info.get('error', '')}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return
    
    # 操作示例说明
    print("\n📝 使用示例:")
    print("""
# 1. 初始化远程连接
client = RemoteVisionAIClient("http://192.168.10.200:9000")

# 2. 检查可用服务和模型
tools = client.get_available_tools()
models = client.get_configured_models()

# 3. 处理图片（使用默认模型）
result = client.analyze_image("/path/to/image.jpg")

# 4. 处理图片（指定特定模型）
result = client.analyze_image(
    "/path/to/image.jpg", 
    model_id="1c2361e3-d011-4417-9139-b30a8acc915a"
)

# 5. 处理PDF（使用配置文件中的模型）
pdf_result = client.process_pdf("/path/to/document.pdf", model_id="指定模型ID")
    """)
    
    print("\n💡 集成提示:")
    print("-" * 40)
    print("1. ✅ MCP 远程服务正常运行")
    print("2. 🔗 您的地址: http://192.168.10.200:9000")
    print("3. 🚀 支持的工具: PDF OCR、图片分析、结构化提取")
    print("4. 🤖 支持使用您保存的模型配置（从 saved_configs.json）")
    print("5. 🛠️ 在您自己的代码中使用 RemoteVisionAIClient 即可调用") 
    print()

def main():
    """主程序入口"""
    print("🚀 Vision AI 远程配置演示")
    print("=" * 60)
    
    demonstrate_usage()
    
    # 测试不同配置方式
    try:
        example_1_direct_configuration()
        example_2_environment_configuration()
        example_3_config_file()
        
    except Exception as e:
        print(f"⚠️ 配置演示时发生错误: {e}")

if __name__ == "__main__":
    main()
