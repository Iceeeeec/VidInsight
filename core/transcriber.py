"""
标题: WhisperTranscriber
说明: 调用远程 Whisper API 将音频转录为文本
时间: 2026-01-14
@author: zhoujunyu
"""

from pathlib import Path
from typing import Optional
import requests
import logging
import time

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
    时间: 2026-01-14
    @author: zhoujunyu
    """
    
    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        初始化远程转录器
        
        Args:
            api_url: 远程 Whisper API 地址，默认使用配置中的地址
            api_key: API 授权密钥，默认使用配置中的密钥
        """
        self.api_url = api_url or Config.REMOTE_WHISPER_API_URL
        self.api_key = api_key or Config.REMOTE_WHISPER_API_KEY
    
    def transcribe(self, audio_path: str, language: str = 'zh') -> str:
        """
        将音频文件转录为文本
        
        通过 POST 请求上传音频文件到远程 Whisper API 进行转录
        使用 OpenAI 兼容的 API 格式 (multipart/form-data)
        
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
            
            # 返回转录文本
            return text
            
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"无法连接到远程 Whisper API 服务: {self.api_url}")
        except requests.exceptions.Timeout:
            raise RuntimeError(f"远程 Whisper API 请求超时")
        except Exception as e:
            raise RuntimeError(f"远程转录失败: {e}")
