"""
标题: ApiKeyManager
说明: API密钥管理器，负责密钥的增删改查和验证
时间: 2026-01-14
@author: zhoujunyu
"""

import json
import secrets
import string
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any


class ApiKeyManager:
    """
    API密钥管理器
    管理远程 API 的访问密钥，支持创建、验证、过期等功能
    """
    
    # 密钥存储文件路径
    KEYS_FILE = Path("./data/api_keys.json")
    
    def __init__(self):
        """
        初始化密钥管理器
        """
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """
        确保存储目录和文件存在
        """
        self.KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not self.KEYS_FILE.exists():
            self._save_data({"keys": []})
    
    def _load_data(self) -> Dict[str, Any]:
        """
        加载密钥数据
        
        Returns:
            Dict: 密钥数据字典
        """
        try:
            with open(self.KEYS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"keys": []}
    
    def _save_data(self, data: Dict[str, Any]):
        """
        保存密钥数据
        
        Args:
            data: 密钥数据字典
        """
        with open(self.KEYS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def generate_key(self) -> str:
        """
        生成新的密钥字符串
        格式: VID-XXXX-XXXX-XXXX
        
        Returns:
            str: 生成的密钥
        """
        chars = string.ascii_uppercase + string.digits
        parts = [''.join(secrets.choice(chars) for _ in range(4)) for _ in range(3)]
        return f"VID-{'-'.join(parts)}"
    
    def create_key(self, name: str, expires_days: Optional[int] = 30) -> Dict[str, Any]:
        """
        创建新密钥
        
        Args:
            name: 密钥名称/备注
            expires_days: 有效期天数，None 表示永不过期
            
        Returns:
            Dict: 创建的密钥信息
        """
        data = self._load_data()
        
        key = self.generate_key()
        now = datetime.now()
        
        key_info = {
            "key": key,
            "name": name,
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "expires_at": (now + timedelta(days=expires_days)).strftime("%Y-%m-%d %H:%M:%S") if expires_days else None,
            "enabled": True,
            "usage_count": 0
        }
        
        data["keys"].insert(0, key_info)
        self._save_data(data)
        
        return key_info
    
    def validate_key(self, key: str, username: Optional[str] = None) -> Dict[str, Any]:
        """
        验证密钥是否有效
        每个密钥最多允许 2 个不同用户使用
        
        Args:
            key: 要验证的密钥
            username: 当前用户名（用于绑定密钥）
            
        Returns:
            Dict: {
                'valid': bool,
                'message': str,
                'key_info': Dict or None
            }
        """
        if not key or not key.strip():
            return {"valid": False, "message": "密钥不能为空", "key_info": None}
        
        key = key.strip().upper()
        data = self._load_data()
        
        for key_info in data.get("keys", []):
            if key_info.get("key") == key:
                # 检查是否已禁用
                if not key_info.get("enabled", True):
                    return {"valid": False, "message": "密钥已被禁用", "key_info": key_info}
                
                # 检查是否已过期
                expires_at = key_info.get("expires_at")
                if expires_at:
                    expire_time = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                    if datetime.now() > expire_time:
                        return {"valid": False, "message": f"密钥已过期 ({expires_at})", "key_info": key_info}
                
                # 初始化 used_by 列表
                if "used_by" not in key_info:
                    key_info["used_by"] = []
                
                # 如果提供了用户名，进行绑定检查
                if username:
                    # 如果用户已绑定该密钥，直接通过
                    if username in key_info["used_by"]:
                        return {"valid": True, "message": "密钥有效", "key_info": key_info}
                    
                    # 检查是否达到使用上限 (2次)
                    if len(key_info["used_by"]) >= 2:
                        return {"valid": False, "message": "该密钥已达到最大使用人数限制 (2人)", "key_info": key_info}
                    
                    # 绑定新用户
                    key_info["used_by"].append(username)
                    key_info["usage_count"] = len(key_info["used_by"])
                    self._save_data(data)
                    return {"valid": True, "message": "密钥验证并绑定成功", "key_info": key_info}
                
                # 如果没提供用户名（仅检查存在性），且未达到上限或只是查询
                # 这里假设仅验证存在性时不占用名额，但通常调用都会传 username
                return {"valid": True, "message": "密钥有效", "key_info": key_info}
        
        return {"valid": False, "message": "密钥不存在", "key_info": None}
    
    def get_all_keys(self) -> List[Dict[str, Any]]:
        """
        获取所有密钥
        
        Returns:
            List[Dict]: 密钥列表
        """
        data = self._load_data()
        keys = data.get("keys", [])
        
        # 添加状态信息
        now = datetime.now()
        for key_info in keys:
            expires_at = key_info.get("expires_at")
            if expires_at:
                expire_time = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                key_info["is_expired"] = now > expire_time
            else:
                key_info["is_expired"] = False
        
        return keys
    
    def delete_key(self, key: str) -> bool:
        """
        删除密钥
        
        Args:
            key: 要删除的密钥
            
        Returns:
            bool: 是否删除成功
        """
        data = self._load_data()
        original_count = len(data.get("keys", []))
        data["keys"] = [k for k in data.get("keys", []) if k.get("key") != key]
        
        if len(data["keys"]) < original_count:
            self._save_data(data)
            return True
        return False
    
    def toggle_key(self, key: str) -> Optional[bool]:
        """
        切换密钥启用/禁用状态
        
        Args:
            key: 密钥
            
        Returns:
            Optional[bool]: 新的启用状态，None 表示密钥不存在
        """
        data = self._load_data()
        
        for key_info in data.get("keys", []):
            if key_info.get("key") == key:
                key_info["enabled"] = not key_info.get("enabled", True)
                self._save_data(data)
                return key_info["enabled"]
        
        return None


# 全局单例
api_key_manager = ApiKeyManager()
