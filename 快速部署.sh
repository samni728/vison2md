#!/bin/bash

# Qwen2.5VL WebUI 快速部署脚本
# API-only模式 - 专为仅使用API调用的场景优化

echo "开始部署Qwen2.5VL WebUI API-only版本..."

# 检查环境
if ! command -v docker-compose &> /dev/null; then
    echo "错误: 请先安装 docker-compose"
    exit 1
fi

# 设置为API-only模式
export DOCKERFILE=Dockerfile.api

echo "使用API-only模式构建（跳过MLX依赖）..."

# 构建镜像
echo "正在构建Docker镜像..."
docker-compose build

if [ $? -eq 0 ]; then
    echo "✅ 构建成功！"
    echo "正在启动服务..."
    
    # 启动服务
    docker-compose up -d
    
    if [ $? -eq 0 ]; then
        echo "✅ 服务启动成功！"
        echo ""
        echo "🌐 Web界面: http://localhost:8000"
        echo "📋 API文档: http://localhost:8000/docs"
        echo ""
        echo "服务正在后台运行。"
        echo ""
        echo "管理命令："
        echo "  停止服务: docker-compose down"
        echo "  查看日志: docker-compose logs -f"
        echo "  重启服务: docker-compose restart"
        echo ""
    else
        echo "❌ 服务启动失败，请检查日志"
        docker-compose logs
    fi
else
    echo "❌ 构建失败，请检查错误信息"
fi
