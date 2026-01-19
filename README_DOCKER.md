# VidInsight Docker 部署指南

本指南将帮助您使用 Docker 和 Docker Compose 快速部署 VidInsight 应用。

## 前置条件

确保您的服务器已安装：

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## 快速开始

1. **配置环境变量**

   复制 `.env.example` (如果有) 或直接创建 `.env` 文件，并填入必要的 API Key：

   ```bash
   # .env
   LLM_API_KEY=your_api_key_here
   LLM_API_BASE=https://api.openai.com/v1
   LLM_MODEL=gpt-3.5-turbo
   WHISPER_API_URL=http://your-whisper-api-url
   ```

2. **构建并启动**

   在项目根目录下运行：

   ```bash
   docker-compose up -d --build
   ```

3. **访问应用**

   打开浏览器访问：`http://localhost:8501` (或服务器 IP:8501)

## 常用命令

- **查看日志**

  ```bash
  docker-compose logs -f
  ```

- **停止服务**

  ```bash
  docker-compose down
  ```

- **重启服务**
  ```bash
  docker-compose restart
  ```

## 数据持久化

- 用户数据和历史记录保存在 `./data` 目录。
- 临时文件保存在 `./temp` 目录。
- 这些目录已挂载到容器中，重启容器不会丢失数据。
