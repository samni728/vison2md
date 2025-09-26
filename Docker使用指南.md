# 🐳 Docker 使用指南

## 📖 概述

本项目已完全支持 Docker 容器化部署，提供了一键启动的解决方案。现在支持**两种部署模式**：

🔸 **完整模式**：支持本地 MLX 模型推理，适用于高性能处理需求  
🔸 **API-only 模式**：轻量级部署，仅用于 API 调用，适用于服务器快速部署

通过 Docker，您可以：

- 🚀 **快速部署**：无需配置 Python 环境
- 🔒 **环境隔离**：避免依赖冲突
- 📦 **便携部署**：在任何支持 Docker 的系统上运行
- 🔄 **易于更新**：通过镜像更新快速升级
- ⚡ **轻量高效**：API-only 模式对整个服务器的资源消耗更少

## 🛠️ 系统要求

### 基础要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 2GB 可用内存
- 至少 1GB 可用磁盘空间

### 推荐配置

- Docker 24.0+
- Docker Compose 2.20+
- 4GB+ 可用内存
- 5GB+ 可用磁盘空间（用于模型缓存）

## 🚀 快速开始

### 方法一：API-only 模式（轻量级，推荐用于 API 调用）

```bash
# 1. 克隆项目（如果还没有）
git clone <项目地址>
cd vision-ai-webui

# 2. 使用 API-only 模式启动服务（跳过MLX依赖）
export DOCKERFILE=Dockerfile.api
docker-compose build
docker-compose up -d

# 或者运行快速部署脚本
./快速部署.sh
```

### 方法二：完整模式（包含本地 MLX 模型支持）

```bash
# 1. 克隆项目（如果还没有）
git clone <项目地址>
cd vision-ai-webui

# 2. 启动完整服务
docker-compose up -d

# 3. 查看服务状态
docker-compose ps

# 4. 查看日志
docker-compose logs -f
```

### 方法三：使用 Docker 命令（API-only 模式）

```bash
# 1. 构建 API-only 镜像
docker build -f Dockerfile.api -t vision-ai-webui-api .

# 2. 运行容器
docker run -d \
  --name vision-ai-webui \
  -p 8000:8000 \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/uploads:/app/uploads \
  vision-ai-webui-api

# 3. 查看容器状态
docker ps

# 4. 查看日志
docker logs -f vision-ai-webui
```

### 方法四：使用 Docker 命令（完整模式）

```bash
# 1. 构建完整镜像
docker build -t vision-ai-webui-full .

# 2. 运行容器
docker run -d \
  --name vision-ai-webui-full \
  -p 8000:8000 \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/uploads:/app/uploads \
  vision-ai-webui-full

# 3. 查看容器状态
docker ps

# 4. 查看日志
docker logs -f vision-ai-webui-full
```

## 🌐 访问应用

启动成功后，在浏览器中访问：

```
http://localhost:8000
```

## 📁 目录结构

```
vision-ai-webui/
├── Dockerfile              # 完整模式Docker镜像构建文件
├── Dockerfile.api          # API-only模式Docker镜像构建文件
├── docker-compose.yml      # Docker Compose 配置（支持两种模式）
├── 快速部署.sh             # 一键API-only模式部署脚本
├── 构建和部署指南.md        # 详细构建指南
├── .dockerignore           # Docker 忽略文件
├── outputs/                # 输出文件目录（挂载到容器）
├── uploads/                # 上传文件目录（挂载到容器）
└── config/                 # 配置文件目录（挂载到容器）
```

## ⚙️ 两种部署模式详解

### 🏗️ API-only 模式（Dockerfile.api）

**特点**：

- ⚡ **构建速度快**：只安装基础依赖，跳过 MLX/机器学习框架
- 🎯 **镜像体积小**：通常只有完整模式的 1/3 大小
- 🚀 **启动更快**：依赖更少，启动时间大幅缩短
- 🔧 **只适合 API 调用**：仅用于调用外部 API 处理文档和图片

**适用场景**：

- 服务器资源有限的环境
- 只需要 API 接口调用的场景
- 轻量级 kubernetes 部署
- 快速原型搭建

### 🏗️ 完整模式（Dockerfile）

**特点**：

- 🔥 **功能完整**：支持本地 MLX 模型推理和 API 调用双重方式
- 📦 **依赖完整**：包含 MLX、PyTorch 等机器学习和推理工具
- 💪 **处理能力更强**：可在无网络的环境下完成推理
- 🔧 **功能全面**：支持本地模型管理

**适用场景**：

- 本地高性能处理
- 离线环境部署
- 对处理速度要求严格的场景
- 企业内网环境

### 🔄 模式切换

```bash
# API-only 模式
export DOCKERFILE=Dockerfile.api
docker-compose build && docker-compose up -d

# 完整模式
export DOCKERFILE=Dockerfile
docker-compose build && docker-compose up -d
```

## 🔧 配置说明

### 端口配置

默认端口是 8000，如需修改：

```yaml
# docker-compose.yml
services:
  vision-ai-webui:
    ports:
      - "8080:8000" # 将本地8080端口映射到容器8000端口
```

### 数据持久化

以下目录会被挂载到宿主机，确保数据持久化：

- `./outputs` → 处理结果文件
- `./uploads` → 临时上传文件
- `./config` → 用户配置和保存的配置

### 环境变量

可以通过环境变量配置应用：

```yaml
# docker-compose.yml
services:
  vision-ai-webui:
    environment:
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
      # 添加其他环境变量
```

## 🎯 使用场景

### 场景 1：本地开发测试

```bash
# 开发模式启动（支持热重载）
docker-compose -f docker-compose.dev.yml up
```

### 场景 2：生产环境部署

```bash
# 生产模式启动
docker-compose -f docker-compose.prod.yml up -d
```

### 场景 3：服务器部署

```bash
# 在服务器上部署
git clone <项目地址>
cd vision-ai-webui
docker-compose up -d

# 设置开机自启
sudo systemctl enable docker
```

## 📊 管理命令

### 基本操作

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 进入容器
docker-compose exec vision-ai-webui bash
```

### 更新和维护

```bash
# 重新构建镜像
docker-compose build --no-cache

# 更新并重启服务
docker-compose up -d --build

# 清理未使用的镜像
docker image prune -f

# 清理所有未使用的资源
docker system prune -f
```

### 数据管理

```bash
# 备份数据
tar -czf backup-$(date +%Y%m%d).tar.gz outputs/ uploads/ config/

# 恢复数据
tar -xzf backup-20240101.tar.gz

# 查看磁盘使用情况
docker system df
```

## 🔍 故障排除

### 常见问题

**问题 1：端口被占用**

```bash
# 查看端口占用
netstat -tlnp | grep 8000

# 修改端口映射
# 编辑 docker-compose.yml 中的 ports 配置
```

**问题 2：权限问题**

```bash
# 修复目录权限
sudo chown -R $USER:$USER outputs/ uploads/ config/

# 或者使用 root 权限运行
docker-compose up -d --user root
```

**问题 3：内存不足**

```bash
# 查看容器资源使用
docker stats vision-ai-webui

# 限制容器内存使用
# 在 docker-compose.yml 中添加：
# deploy:
#   resources:
#     limits:
#       memory: 2G
```

**问题 4：构建失败**

```bash
# 清理构建缓存
docker builder prune -f

# 重新构建
docker-compose build --no-cache
```

### 日志查看

```bash
# 查看实时日志
docker-compose logs -f

# 查看最近的日志
docker-compose logs --tail=100

# 查看特定服务的日志
docker-compose logs vision-ai-webui
```

## 🚀 高级配置

### 自定义 Dockerfile

如果需要自定义构建，可以修改 `Dockerfile`：

```dockerfile
# 使用不同的基础镜像
FROM python:3.11-slim

# 安装额外的系统依赖
RUN apt-get update && apt-get install -y \
    your-additional-package

# 自定义启动命令
CMD ["python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 多环境配置

创建不同环境的配置文件：

```bash
# 开发环境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 生产环境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 健康检查

容器内置了健康检查：

```bash
# 查看健康状态
docker inspect --format='{{.State.Health.Status}}' vision-ai-webui

# 手动健康检查
curl -f http://localhost:8000/ || echo "Service is down"
```

## 📈 性能优化

### 资源限制

```yaml
# docker-compose.yml
services:
  vision-ai-webui:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "2.0"
        reservations:
          memory: 2G
          cpus: "1.0"
```

### 缓存优化

```yaml
# docker-compose.yml
services:
  vision-ai-webui:
    volumes:
      # 缓存目录
      - model_cache:/app/.cache
      - pip_cache:/root/.cache/pip

volumes:
  model_cache:
  pip_cache:
```

## 🔒 安全建议

1. **网络安全**

   - 使用防火墙限制访问
   - 考虑使用反向代理（如 Nginx）

2. **数据安全**

   - 定期备份重要数据
   - 使用加密存储敏感信息

3. **容器安全**
   - 定期更新基础镜像
   - 使用非 root 用户运行

## 📚 相关资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [项目 GitHub 仓库](项目地址)

## 🆘 获取帮助

如果遇到问题，请：

1. 查看本文档的故障排除部分
2. 检查项目的 GitHub Issues
3. 提交新的 Issue 描述问题

---

**享受使用 Docker 部署的 Vision AI 批量处理工具！** 🎉
