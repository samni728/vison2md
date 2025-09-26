#!/usr/bin/env python3
"""
远程 Vision AI MCP 服务连接测试脚本
"""

import requests
import sys
import time
from argparse import ArgumentParser

def test_mcp_connection(base_url="http://192.168.10.200:9000"):
    """测试 MCP 连接"""
    print(f"🔍 测试 MCP 服务连接: {base_url}")
    print("=" * 50)
    
    # 测试基础连接
    try:
        print("1. 测试基础服务连接...")
        response = requests.get(f"{base_url}/", timeout=10)
        
        if response.status_code == 200:
            print("   ✅ 服务可访问")
            service_info = response.json()
            print(f"   📊 服务信息: {service_info}")
        else:
            print(f"   ❌ 服务响应错误: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectTimeout:
        print("   ❌ 连接超时")
        print("   💡 检查服务是否在远程地址运行")
        return False
    except requests.exceptions.ConnectionError:
        print("   ❌ 连接被拒绝")
        print("   💡 检查远程地址和端口是否正确")
        return False
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        return False
    
    # 测试 MCP 工具列表
    try:
        print("\n2. 测试 MCP 工具连接...")
        response = requests.get(f"{base_url}/mcp/tools", timeout=10)
        
        if response.status_code == 200:
            tools = response.json()
            print("   ✅ 工具列表可访问")
            print(f"   📋 可用工具数量: {len(tools.get('tools', []))}")
            
            for tool in tools.get('tools', []):
                print(f"      - {tool.get('name', 'N/A')}: {tool.get('description', 'N/A')}")
        else:
            print(f"   ❌ 工具列表错误: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ 工具列表获取失败: {e}")
        return False
    
    print("\n🎉 远程 MCP 服务连接正常!")
    return True

def test_api_endpoints(base_url="http://192.168.10.200:9000"):
    """测试 API 端点响应"""
    print(f"\n📋 测试 API 端点响应: {base_url}")
    print("-" * 40)
    
    endpoints = [
        "/",
        "/mcp/tools"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            status = "✅" if response.status_code == 200 else "❌"
            print(f"   {status} {endpoint}: HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ {endpoint}: {str(e)[:50]}...")

def check_network_status(server_url):
    """检查网络状态"""
    print(f"\n🌐 网络状态检查")
    print("-" * 30)
    
    import urllib.request
    import socket
    
    # 提取主机名和端口
    from urllib.parse import urlparse
    parsed = urlparse(server_url)
    hostname = parsed.hostname
    port = parsed.port or 9000
    
    try:
        import subprocess
        import platform
        
        # ping 测试（根据系统平台）
        os_type = platform.system().lower()
        if os_type in ['linux', 'darwin']:  # Linux 和 macOS
            ping_command = ['ping', '-c', '3', hostname]
        else:  # Windows
            ping_command = ['ping', '-n', '3', hostname]
        
        print(f"   🔄 使用 ping 测试: {hostname}")
        result = subprocess.run(
            ping_command,
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            print("   ✅ 网络连通性正常")
        else:
            print("   ⚠️  ping 测试失败，但服务仍可尝试访问")
            
    except Exception as e:
        print(f"   ℹ️  网络检查跳过: {e}")
    
    # 端口连通性测试
    try:
        print(f"   🔌 测试端口连接: {hostname}:{port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((hostname, port))
        sock.close()
        
        if result == 0:
            print("   ✅ 端口可达")
        else:
            print("   ❌ 端口不可达")
            
    except Exception as e:
        print(f"   ⚠️  端口测试跳过: {e}")

def main():
    """主程序入口"""
    parser = ArgumentParser(description="测试远程 Vision AI MCP 服务")
    parser.add_argument(
        "--url",
        default="http://192.168.10.200:9000", 
        help="目标 MCP 服务地址"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )
    
    args = parser.parse_args()
    
    try:
        # 显示配置信息
        print("🌐 远程 MCP 服务连接测试")
        print(f"🔗 目标地址: {args.url}")
        print(f"⏰ 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 网络状态检查
        if args.verbose:
            check_network_status(args.url)
        
        # MCP 服务测试
        success = test_mcp_connection(args.url)
        
        if success:
            # API 端点详细测试
            if args.verbose:
                test_api_endpoints(args.url)
            
            print("\n💡 下一步操作:")
            print("1. 在您的代码中使用远程客户端配置")
            print("   client = RemoteVisionAIClient('http://192.168.10.200:9000')")
            print("2. 或者修改环境变量")
            print("   export VISION_AI_URL='http://192.168.10.200:9000'")
            print("\n✅ 配置测试完成，可以正常使用远程 MCP 服务！")
        else:
            print("\n❌ 远程连接测试失败")
            print("\n💡 故障排查:")
            print("1. 确认服务是否在指定地址运行")
            print("2. 检查防火墙和网络连接")
            print("3. 验证服务端口映射是否正确")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试程序错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
