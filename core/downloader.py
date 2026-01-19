"""
标题: BilibiliDownloader
说明: B站视频/音频/字幕下载器，使用 yt-dlp 实现
时间: 2026-01-14
@author: zhoujunyu
"""

import os
import json
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

import yt_dlp

from config import Config
from utils.helpers import ensure_dir, sanitize_filename, extract_video_id


@dataclass
class DownloadResult:
    """
    下载结果数据类
    """
    video_id: str           # 视频 ID
    title: str              # 视频标题
    duration: float         # 视频时长（秒）
    text: Optional[str]     # 字幕文本（如果有）
    audio_path: Optional[str]  # 音频文件路径（如果无字幕）
    has_subtitle: bool      # 是否有字幕


class BilibiliDownloader:
    """
    B站视频下载器
    优先提取字幕，无字幕时下载音频
    """
    
    def __init__(self, temp_dir: Optional[Path] = None):
        """
        初始化下载器
        
        Args:
            temp_dir: 临时文件目录，默认使用配置中的目录
        """
        self.temp_dir = temp_dir or Config.get_temp_dir()
        ensure_dir(self.temp_dir)
    
    def download(self, url: str) -> DownloadResult:
        """
        下载视频内容（优先字幕，其次音频）
        
        Args:
            url: B站视频链接
            
        Returns:
            DownloadResult: 下载结果
            
        Raises:
            ValueError: 无效的视频链接
            RuntimeError: 下载失败
        """
        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError(f"无效的B站视频链接: {url}")
        
        # 首先获取视频信息
        info = self._get_video_info(url)
        title = info.get('title', video_id)
        duration = info.get('duration', 0)
        
        # 尝试提取字幕
        subtitle_text = self._extract_subtitle(info)
        
        if subtitle_text:
            return DownloadResult(
                video_id=video_id,
                title=title,
                duration=duration,
                text=subtitle_text,
                audio_path=None,
                has_subtitle=True
            )
        
        # 无字幕，下载音频
        audio_path = self._download_audio(url, video_id)
        
        return DownloadResult(
            video_id=video_id,
            title=title,
            duration=duration,
            text=None,
            audio_path=audio_path,
            has_subtitle=False
        )
    
    def _get_video_info(self, url: str) -> dict:
        """
        获取视频元信息
        
        Args:
            url: 视频链接
            
        Returns:
            dict: 视频信息字典
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['zh-Hans', 'zh-CN', 'zh', 'en'],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            raise RuntimeError(f"获取视频信息失败: {e}")
    
    def _extract_subtitle(self, info: dict) -> Optional[str]:
        """
        从视频信息中提取字幕文本
        
        Args:
            info: 视频信息字典
            
        Returns:
            str: 字幕文本，无字幕返回 None
        """
        subtitles = info.get('subtitles', {})
        automatic_captions = info.get('automatic_captions', {})
        
        # 合并字幕源，优先手动字幕
        all_subs = {**automatic_captions, **subtitles}
        
        # 按优先级查找字幕
        priority_langs = ['zh-Hans', 'zh-CN', 'zh', 'en']
        
        for lang in priority_langs:
            if lang in all_subs:
                sub_info = all_subs[lang]
                # 获取字幕内容
                for sub in sub_info:
                    if sub.get('ext') in ['json3', 'srv3', 'vtt', 'srt']:
                        return self._fetch_subtitle_content(sub.get('url'))
        
        return None
    
    def _fetch_subtitle_content(self, sub_url: str) -> Optional[str]:
        """
        获取字幕内容并转换为纯文本
        
        Args:
            sub_url: 字幕文件 URL
            
        Returns:
            str: 纯文本字幕
        """
        try:
            import urllib.request
            with urllib.request.urlopen(sub_url, timeout=30) as response:
                content = response.read().decode('utf-8')
                
            # 简单提取文本（移除时间戳等）
            lines = []
            for line in content.split('\n'):
                line = line.strip()
                # 跳过时间戳行和空行
                if not line or '-->' in line or line.isdigit():
                    continue
                # 移除 HTML 标签
                import re
                clean_line = re.sub(r'<[^>]+>', '', line)
                if clean_line:
                    lines.append(clean_line)
            
            return '\n'.join(lines)
        except Exception:
            return None
    
    def _download_audio(self, url: str, video_id: str) -> str:
        """
        下载视频音频并转换为 MP3
        
        Args:
            url: 视频链接
            video_id: 视频 ID
            
        Returns:
            str: 音频文件路径
        """
        output_path = self.temp_dir / f"{sanitize_filename(video_id)}.mp3"
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio/best',
            'outtmpl': str(self.temp_dir / f"{sanitize_filename(video_id)}.%(ext)s"),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if output_path.exists():
                return str(output_path)
            else:
                raise RuntimeError("音频文件未生成")
                
        except Exception as e:
            raise RuntimeError(f"下载音频失败: {e}")
    
    def cleanup(self, audio_path: str) -> None:
        """
        清理临时音频文件
        
        Args:
            audio_path: 音频文件路径
        """
        try:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass  # 忽略清理错误
