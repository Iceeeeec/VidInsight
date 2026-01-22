"""
标题: WhisperTranscriber
说明: 调用远程 Whisper API 将音频转录为文本
时间: 2026-01-14
@author: zhoujunyu
"""

from pathlib import Path
from typing import Optional, List
import requests
import logging
import time
import subprocess
import tempfile
import json

from config import Config

# 配置日志记录器
logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    Whisper 语音转文字转录器
    通过调用远程 Whisper API 服务实现语音转录
    """
    
    def __init__(self, api_url: Optional[str] = None):
        """
        初始化转录器
        
        Args:
            api_url: Whisper API 服务地址，默认使用配置中的地址
        """
        self.api_url = api_url or Config.WHISPER_API_URL
    
    def _check_service(self) -> bool:
        """
        检查 Whisper API 服务是否可用
        
        Returns:
            bool: 服务是否可用
        """
        try:
            response = requests.get(self.api_url)
            if response.status_code == 200:
                data = response.json()
                return data.get('status') == 'ok'
            return False
        except Exception:
            return False
    
    def transcribe(self, audio_path: str, language: str = 'zh') -> str:
        """
        将音频文件转录为文本
        
        通过 POST /transcribe 接口上传音频文件进行转录
        
        Args:
            audio_path: 音频文件路径
            language: 音频语言，默认中文
            
        Returns:
            str: 转录的文本内容
            
        Raises:
            FileNotFoundError: 音频文件不存在
            RuntimeError: 转录失败或 API 调用失败
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        try:
            # 构建请求 URL
            url = f"{self.api_url}/transcribe"
            
            # 准备文件和参数
            with open(audio_file, 'rb') as f:
                files = {'file': (audio_file.name, f, 'audio/mpeg')}
                data = {'language': language}
                
                # 发送请求
                response = requests.post(url, files=files, data=data)
            
            # 检查响应状态
            if response.status_code != 200:
                raise RuntimeError(f"API 请求失败，状态码: {response.status_code}")
            
            # 解析响应
            result = response.json()
            
            if not result.get('success'):
                error_msg = result.get('error', '未知错误')
                raise RuntimeError(f"转录失败: {error_msg}")
            
            # 返回转录文本
            return result.get('text', '')
            
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"无法连接到 Whisper API 服务: {self.api_url}")
        except Exception as e:
            raise RuntimeError(f"转录失败: {e}")
    
    def transcribe_with_timestamps(self, audio_path: str, language: str = 'zh') -> list:
        """
        将音频文件转录为带时间戳的文本段落
        
        通过 POST /transcribe/detail 接口获取详细转录结果
        
        Args:
            audio_path: 音频文件路径
            language: 音频语言
            
        Returns:
            list: 包含 {'start', 'end', 'text'} 的列表
            
        Raises:
            FileNotFoundError: 音频文件不存在
            RuntimeError: 转录失败或 API 调用失败
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        try:
            # 构建请求 URL（使用详细转录接口）
            url = f"{self.api_url}/transcribe/detail"
            
            # 准备文件和参数
            with open(audio_file, 'rb') as f:
                files = {'file': (audio_file.name, f, 'audio/mpeg')}
                data = {'language': language}
                
                # 发送请求
                response = requests.post(url, files=files, data=data)
            
            # 检查响应状态
            if response.status_code != 200:
                raise RuntimeError(f"API 请求失败，状态码: {response.status_code}")
            
            # 解析响应
            result = response.json()
            
            if not result.get('success'):
                error_msg = result.get('error', '未知错误')
                raise RuntimeError(f"转录失败: {error_msg}")
            
            # 提取带时间戳的段落
            segments = []
            for seg in result.get('segments', []):
                segments.append({
                    'start': seg['start'],
                    'end': seg['end'],
                    'text': seg['text'].strip()
                })
            
            return segments
            
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"无法连接到 Whisper API 服务: {self.api_url}")
        except Exception as e:
            raise RuntimeError(f"转录失败: {e}")
    
    def transcribe_from_url(self, audio_url: str, language: str = 'zh') -> str:
        """
        通过音频 URL 进行转录（无需下载到本地）
        
        通过 POST /transcribe/url 接口直接传递音频 URL
        
        Args:
            audio_url: 音频文件的 URL 地址
            language: 音频语言，默认中文
            
        Returns:
            str: 转录的文本内容
            
        Raises:
            RuntimeError: 转录失败或 API 调用失败
        """
        try:
            # 构建请求 URL
            url = f"{self.api_url}/transcribe/url"
            
            # 准备 JSON 请求体
            payload = {
                'url': audio_url,
                'language': language
            }
            
            # 发送请求
            response = requests.post(url, json=payload)
            
            # 检查响应状态
            if response.status_code != 200:
                raise RuntimeError(f"API 请求失败，状态码: {response.status_code}")
            
            # 解析响应
            result = response.json()
            
            if not result.get('success'):
                error_msg = result.get('error', '未知错误')
                raise RuntimeError(f"转录失败: {error_msg}")
            
            return result.get('text', '')
            
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"无法连接到 Whisper API 服务: {self.api_url}")
        except Exception as e:
            raise RuntimeError(f"转录失败: {e}")


class RemoteWhisperTranscriber:
    """
    标题: RemoteWhisperTranscriber
    说明: 远程 Whisper API 转录器，使用 OpenAI 兼容的 API 格式
          支持自动分片处理超过 25 分钟的长音频
    时间: 2026-01-14
    @author: zhoujunyu
    """
    
    # 最大音频时长（秒），gpt-4o-transcribe 限制 1500 秒
    MAX_AUDIO_DURATION = 1400  # 保留 100 秒余量
    
    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        初始化远程转录器
        
        Args:
            api_url: 远程 Whisper API 地址，默认使用配置中的地址
            api_key: API 授权密钥，默认使用配置中的密钥
        """
        self.api_url = api_url or Config.REMOTE_WHISPER_API_URL
        self.api_key = api_key or Config.REMOTE_WHISPER_API_KEY
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """
        获取音频文件时长
        
        使用 ffprobe 获取音频文件的时长信息
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            float: 音频时长（秒）
            
        Raises:
            RuntimeError: 无法获取音频时长
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"ffprobe 执行失败: {result.stderr}")
            
            data = json.loads(result.stdout)
            duration = float(data['format']['duration'])
            return duration
            
        except Exception as e:
            logger.warning(f"[远程转录] 无法获取音频时长: {e}")
            # 返回 0 表示无法检测，将尝试直接转录
            return 0
    
    def _split_audio(self, audio_path: str, max_duration: int = None) -> List[str]:
        """
        将长音频分割成多个片段
        
        使用 ffmpeg 将音频按指定时长分割，每个片段保存为临时文件
        
        Args:
            audio_path: 音频文件路径
            max_duration: 每个片段最大时长（秒），默认使用 MAX_AUDIO_DURATION
            
        Returns:
            List[str]: 分割后的音频片段文件路径列表
            
        Raises:
            RuntimeError: 音频分割失败
        """
        if max_duration is None:
            max_duration = self.MAX_AUDIO_DURATION
        
        audio_file = Path(audio_path)
        temp_dir = Config.get_temp_dir()
        
        # 获取总时长
        total_duration = self._get_audio_duration(audio_path)
        if total_duration <= 0:
            raise RuntimeError(f"无法获取音频时长: {audio_path}")
        
        # 计算需要分割的片段数
        num_segments = int(total_duration // max_duration) + 1
        logger.info(f"[远程转录] 音频时长 {total_duration:.1f}s，将分割为 {num_segments} 个片段")
        
        segment_files = []
        
        for i in range(num_segments):
            start_time = i * max_duration
            
            # 生成临时文件名
            segment_file = temp_dir / f"segment_{i}_{audio_file.stem}.mp3"
            
            # 使用 ffmpeg 分割音频
            cmd = [
                'ffmpeg',
                '-y',  # 覆盖已存在的文件
                '-i', audio_path,
                '-ss', str(start_time),
                '-t', str(max_duration),
                '-acodec', 'libmp3lame',
                '-q:a', '2',
                str(segment_file)
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"[远程转录] ffmpeg 分割失败: {result.stderr}")
                    raise RuntimeError(f"音频分割失败: 片段 {i+1}")
                
                segment_files.append(str(segment_file))
                logger.info(f"[远程转录] 已创建片段 {i+1}/{num_segments}: {segment_file.name}")
                
            except Exception as e:
                # 清理已创建的临时文件
                for f in segment_files:
                    try:
                        Path(f).unlink()
                    except:
                        pass
                raise RuntimeError(f"音频分割失败: {e}")
        
        return segment_files
    
    def _transcribe_single(self, audio_path: str, language: str = 'zh') -> str:
        """
        转录单个音频文件（不进行分片）
        
        Args:
            audio_path: 音频文件路径
            language: 音频语言，默认中文
            
        Returns:
            str: 转录的文本内容
            
        Raises:
            RuntimeError: 转录失败
        """
        audio_file = Path(audio_path)
        
        # 准备请求头
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        
        # 记录开始时间
        start_time = time.time()
        file_size = audio_file.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"[远程转录] 开始转录文件: {audio_file.name} (大小: {file_size:.2f} MB)")
        
        # 准备文件和参数
        with open(audio_file, 'rb') as f:
            files = {'file': (audio_file.name, f, 'audio/mpeg')}
            data = {'model': 'gpt-4o-transcribe'}
            
            # 发送请求 (不设置超时，等待服务器处理完成)
            response = requests.post(
                self.api_url,
                headers=headers,
                files=files,
                data=data,
                timeout=None  # 无超时限制
            )
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        
        # 检查响应状态
        if response.status_code != 200:
            error_detail = response.text[:200] if response.text else '无详细信息'
            logger.error(f"[远程转录] 失败 - 状态码: {response.status_code}, 耗时: {elapsed_time:.2f}秒")
            raise RuntimeError(f"API 请求失败，状态码: {response.status_code}，详情: {error_detail}")
        
        # 解析响应 (OpenAI 格式返回 {"text": "..."})
        result = response.json()
        text = result.get('text', '')
        
        # 记录成功日志
        text_length = len(text)
        logger.info(f"[远程转录] 完成 - 耗时: {elapsed_time:.2f}秒, 输出字符数: {text_length}")
        
        return text
    
    def transcribe(self, audio_path: str, language: str = 'zh') -> str:
        """
        将音频文件转录为文本
        
        通过 POST 请求上传音频文件到远程 Whisper API 进行转录
        使用 OpenAI 兼容的 API 格式 (multipart/form-data)
        
        对于超过 25 分钟的长音频，自动进行分片处理
        
        Args:
            audio_path: 音频文件路径
            language: 音频语言，默认中文（注：此参数暂未使用，由模型自动检测）
            
        Returns:
            str: 转录的文本内容
            
        Raises:
            FileNotFoundError: 音频文件不存在
            RuntimeError: 转录失败或 API 调用失败
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        if not self.api_key:
            raise RuntimeError("远程 Whisper API Key 未配置，请在 .env 中设置 REMOTE_WHISPER_API_KEY")
        
        try:
            # 检测音频时长
            duration = self._get_audio_duration(audio_path)
            
            # 如果时长小于限制或无法检测，直接转录
            if duration <= 0 or duration <= self.MAX_AUDIO_DURATION:
                if duration > 0:
                    logger.info(f"[远程转录] 音频时长 {duration:.1f}s，无需分片")
                return self._transcribe_single(audio_path, language)
            
            # 需要分片处理
            logger.info(f"[远程转录] 音频时长 {duration:.1f}s 超过限制 {self.MAX_AUDIO_DURATION}s，启用分片转录")
            
            # 分割音频
            segment_files = self._split_audio(audio_path)
            
            # 逐个转录
            transcripts = []
            for i, segment_file in enumerate(segment_files):
                logger.info(f"[远程转录] 正在转录片段 {i+1}/{len(segment_files)}")
                try:
                    text = self._transcribe_single(segment_file, language)
                    transcripts.append(text)
                except Exception as e:
                    logger.error(f"[远程转录] 片段 {i+1} 转录失败: {e}")
                    raise
                finally:
                    # 删除临时片段文件
                    try:
                        Path(segment_file).unlink()
                        logger.debug(f"[远程转录] 已删除临时文件: {segment_file}")
                    except:
                        pass
            
            # 合并转录结果
            full_text = '\n'.join(transcripts)
            logger.info(f"[远程转录] 分片转录完成，共 {len(transcripts)} 个片段，总字符数: {len(full_text)}")
            
            return full_text
            
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"无法连接到远程 Whisper API 服务: {self.api_url}")
        except requests.exceptions.Timeout:
            raise RuntimeError(f"远程 Whisper API 请求超时")
        except Exception as e:
            raise RuntimeError(f"远程转录失败: {e}")
