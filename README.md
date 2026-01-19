# VidInsight - B 站视频智能笔记助手 🎬

VidInsight 是一个基于 Streamlit 的智能视频笔记工具，专为 Bilibili 用户设计。它利用 AI 技术自动提取视频内容，生成结构化的摘要和思维导图，帮助用户高效获取视频核心知识。

## ✨ 主要功能

- **视频智能分析**: 支持输入 Bilibili 视频链接 (BV 号或完整 URL)，自动下载并提取音频。
- **AI 语音转录**: 集成 Whisper API，提供高精度的语音转文字服务，支持生成带时间戳的逐字稿。
- **智能摘要生成**: 利用大语言模型 (LLM) 深度分析视频内容，生成精炼的文字摘要。
- **交互式思维导图**: 自动生成可视化的思维导图 (Markmap)，支持缩放、拖拽和节点折叠，直观展示知识脉络。
- **历史记录管理**:
  - 自动保存分析记录，随时回看。
  - 支持搜索、删除历史记录。
  - 支持历史数据的导出 (JSON) 与导入备份。
- **多格式导出**: 提供摘要 (TXT)、思维导图 (HTML)、完整笔记 (Markdown) 和原文 (TXT) 的下载。
- **用户系统**: 包含完整的用户注册、登录、密码修改及会话管理功能。

## 🛠️ 技术栈

- **前端/应用框架**: [Streamlit](https://streamlit.io/)
- **视频处理**: [yt-dlp](https://github.com/yt-dlp/yt-dlp), [ffmpeg-python](https://github.com/kkroening/ffmpeg-python)
- **AI/LLM**: OpenAI API (用于摘要与导图生成)
- **语音转录**: Whisper API (远程调用)
- **可视化**: Streamlit Markmap
- **数据存储**: 本地 JSON 文件存储 (用户数据与历史记录)

## 📂 项目结构

```
SummaView/
├── app.py                 # 应用入口与 UI 逻辑
├── config.py              # 配置管理
├── requirements.txt       # 项目依赖
├── core/                  # 核心处理模块
│   ├── downloader.py      # 视频下载器
│   ├── transcriber.py     # Whisper API 转录客户端
│   ├── llm_processor.py   # LLM 摘要与导图生成
│   └── video_processor.py # 视频处理流程控制器
├── utils/                 # 工具模块
│   ├── user_manager.py    # 用户认证与管理
│   ├── history.py         # 历史记录管理
│   └── helpers.py         # 通用辅助函数
├── data/                  # 数据存储目录 (用户/历史)
└── temp/                  # 临时文件目录
```

## 🚀 快速开始

### 1. 环境准备

确保已安装 Python 3.8+ 和 FFmpeg。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境

在项目根目录创建 `.env` 文件，并配置以下必要信息：

```env
# LLM 配置 (OpenAI 或 兼容接口)
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
LLM_API_BASE=https://api.openai.com/v1  # 可选，默认为 OpenAI 官方
LLM_MODEL=gpt-3.5-turbo                 # 可选

# Whisper API 配置
WHISPER_API_URL=http://your-whisper-api-server:8000
```

### 4. 运行应用

```bash
streamlit run app.py
```

启动后，在浏览器访问显示的地址 (通常是 `http://localhost:8501`) 即可使用。

---

_注意：本项目依赖外部 Whisper API 服务进行语音转录，请确保配置了正确的 `WHISPER_API_URL`。_
"# VidInsight" 
