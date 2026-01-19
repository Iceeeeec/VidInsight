"""
标题: VideoProcessor
说明: 视频处理主流程控制器，整合下载、转录、分析三个模块
时间: 2026-01-14
@author: zhoujunyu
"""

from typing import Callable, Optional
from dataclasses import dataclass
from enum import Enum

from .downloader import BilibiliDownloader, DownloadResult
from .transcriber import WhisperTranscriber
from .llm_processor import LLMProcessor, AnalysisResult


class ProcessingStatus(Enum):
    """
    处理状态枚举
    """
    IDLE = "idle"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ProcessingResult:
    """
    完整处理结果数据类
    """
    video_id: str           # 视频 ID
    title: str              # 视频标题
    duration: float         # 视频时长
    has_subtitle: bool      # 是否有原生字幕
    transcript: str         # 文本内容
    summary: str            # 摘要
    mindmap: str            # 思维导图 Markdown
    mindmap_html: str       # 思维导图 HTML（可在浏览器中打开）
    notes: str              # 完整 Markdown 笔记
    status: ProcessingStatus  # 处理状态


class VideoProcessor:
    """
    视频处理主控制器
    整合下载、转录、分析三个步骤，提供统一的处理接口
    """
    
    def __init__(
        self,
        downloader: Optional[BilibiliDownloader] = None,
        transcriber: Optional[WhisperTranscriber] = None,
        llm_processor: Optional[LLMProcessor] = None
    ):
        """
        初始化处理器
        
        Args:
            downloader: 下载器实例，默认新建
            transcriber: 转录器实例，默认新建
            llm_processor: LLM 处理器实例，默认新建
        """
        self.downloader = downloader or BilibiliDownloader()
        self.transcriber = transcriber or WhisperTranscriber()
        self.llm_processor = llm_processor  # 延迟初始化
        
        self.status = ProcessingStatus.IDLE
        self._status_callback: Optional[Callable[[ProcessingStatus, str, int], None]] = None
    
    def set_status_callback(self, callback: Callable[[ProcessingStatus, str, int], None]):
        """
        设置状态回调函数
        
        Args:
            callback: 回调函数，接收 (status, message, progress) 参数
        """
        self._status_callback = callback
    
    def _update_status(self, status: ProcessingStatus, message: str = "", progress: int = 0):
        """
        更新处理状态并触发回调
        
        Args:
            status: 新状态
            message: 状态消息
            progress: 进度百分比 (0-100)
        """
        self.status = status
        if self._status_callback:
            self._status_callback(status, message, progress)
    
    def process(self, url: str) -> ProcessingResult:
        """
        处理视频的完整流程
        
        Args:
            url: B站视频链接
            
        Returns:
            ProcessingResult: 完整处理结果
            
        Raises:
            ValueError: 无效的视频链接
            RuntimeError: 处理过程中出错
        """
        audio_path = None
        
        try:
            # 步骤 1: 下载内容 (0-30%)
            self._update_status(ProcessingStatus.DOWNLOADING, "正在获取视频信息...", 5)
            download_result = self.download_content(url)
            self._update_status(ProcessingStatus.DOWNLOADING, "下载完成", 30)
            
            # 步骤 2: 获取文本（字幕或转录）(30-60%)
            if download_result.has_subtitle:
                transcript = download_result.text
                self._update_status(ProcessingStatus.TRANSCRIBING, "已获取视频字幕", 60)
            else:
                self._update_status(ProcessingStatus.TRANSCRIBING, "正在转录音频...", 40)
                transcript = self.transcribe(download_result.audio_path)
                audio_path = download_result.audio_path
                self._update_status(ProcessingStatus.TRANSCRIBING, "转录完成", 60)
            
            # 步骤 3: LLM 分析 (60-90%)
            self._update_status(ProcessingStatus.ANALYZING, "正在生成摘要和思维导图...", 70)
            analysis_result = self.analyze(transcript, download_result.title)
            self._update_status(ProcessingStatus.ANALYZING, "分析完成", 95)
            
            # 完成 (100%)
            self._update_status(ProcessingStatus.COMPLETED, "处理完成！", 100)
            
            # 生成完整笔记
            notes = self._generate_notes(
                title=download_result.title,
                video_id=download_result.video_id,
                duration=download_result.duration,
                has_subtitle=download_result.has_subtitle,
                summary=analysis_result.summary,
                mindmap=analysis_result.mindmap,
                transcript=transcript
            )
            
            # 生成思维导图 HTML
            from utils.helpers import generate_mindmap_html
            mindmap_html = generate_mindmap_html(analysis_result.mindmap, download_result.title)
            
            return ProcessingResult(
                video_id=download_result.video_id,
                title=download_result.title,
                duration=download_result.duration,
                has_subtitle=download_result.has_subtitle,
                transcript=transcript,
                summary=analysis_result.summary,
                mindmap=analysis_result.mindmap,
                mindmap_html=mindmap_html,
                notes=notes,
                status=ProcessingStatus.COMPLETED
            )
            
        except Exception as e:
            self._update_status(ProcessingStatus.ERROR, f"处理失败: {str(e)}")
            raise
            
        finally:
            # 清理临时文件
            if audio_path:
                self.downloader.cleanup(audio_path)
    
    def download_content(self, url: str) -> DownloadResult:
        """
        下载视频内容（字幕或音频）
        
        Args:
            url: 视频链接
            
        Returns:
            DownloadResult: 下载结果
        """
        return self.downloader.download(url)
    
    def transcribe(self, audio_path: str) -> str:
        """
        转录音频为文本
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            str: 转录文本
        """
        return self.transcriber.transcribe(audio_path)
    
    def analyze(self, text: str, title: str = "") -> AnalysisResult:
        """
        使用 LLM 分析文本
        
        Args:
            text: 文本内容
            title: 视频标题
            
        Returns:
            AnalysisResult: 分析结果
        """
        # 延迟初始化 LLM 处理器
        if self.llm_processor is None:
            self.llm_processor = LLMProcessor()
        
        return self.llm_processor.analyze(text, title)
    
    def _generate_notes(
        self,
        title: str,
        video_id: str,
        duration: float,
        has_subtitle: bool,
        summary: str,
        mindmap: str,
        transcript: str
    ) -> str:
        """
        生成完整的 Markdown 格式笔记
        
        整合视频信息、摘要和思维导图
        
        Args:
            title: 视频标题
            video_id: 视频 ID
            duration: 视频时长（秒）
            has_subtitle: 是否有原生字幕
            summary: 摘要内容
            mindmap: 思维导图 Markdown
            transcript: 原文内容（保留参数但不使用）
            
        Returns:
            str: 完整的 Markdown 笔记
        """
        from utils.helpers import format_duration
        from datetime import datetime
        
        # 格式化时长
        duration_str = format_duration(duration)
        
        # 字幕来源
        source_str = "原生字幕" if has_subtitle else "AI 语音转录"
        
        # 当前时间
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 构建完整笔记（思维导图保留 Markdown 列表格式，HTML 版本单独下载）
        notes = f"""# {title}

> **视频信息**
> - 📺 视频 ID: `{video_id}`
> - ⏱️ 时长: {duration_str}
> - 📝 字幕来源: {source_str}
> - 📅 生成时间: {now_str}
> - 🔗 链接: https://www.bilibili.com/video/{video_id}

---

## 📋 内容摘要

{summary}

---

## 🧠 思维导图

> � 提示：下载思维导图 HTML 文件可在浏览器中查看交互式思维导图

{mindmap}

---

*由 VidInsight 自动生成*
"""
        return notes

