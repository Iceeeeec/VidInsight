"""
标题: Config
说明: 配置管理类，从环境变量加载配置
时间: 2026-01-14
@author: zhoujunyu
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Config:
    """
    应用配置类
    从环境变量读取配置，提供默认值
    """
    
    # LLM API 配置 (Gemini 中转站 - OpenAI 兼容格式)
    LLM_API_KEY: str = os.getenv('LLM_API_KEY', '')
    LLM_API_BASE: str = os.getenv('LLM_API_BASE', 'https://jeniya.top/v1')
    LLM_MODEL: str = os.getenv('LLM_MODEL', 'gemini-2.5-flash')
    
    # Whisper API 配置（远程服务）
    WHISPER_API_URL: str = os.getenv('WHISPER_API_URL', 'http://149.88.94.184:8000')
    
    # 临时文件目录
    TEMP_DIR: Path = Path(os.getenv('TEMP_DIR', './temp'))
    
    # Token 限制
    MAX_INPUT_TOKENS: int = int(os.getenv('MAX_INPUT_TOKENS', '8000'))
    
    @classmethod
    def validate(cls) -> bool:
        """
        验证必要配置是否已设置
        
        Returns:
            bool: 配置是否有效
        """
        if not cls.LLM_API_KEY:
            return False
        return True
    
    @classmethod
    def get_temp_dir(cls) -> Path:
        """
        获取临时目录，不存在则创建
        
        Returns:
            Path: 临时目录路径
        """
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        return cls.TEMP_DIR
