"""
标题: UserManager
说明: 用户管理模块，负责用户注册、登录和密码验证
时间: 2026-01-14
@author: zhoujunyu
"""

import json
import os
import re
import hashlib
from pathlib import Path
from typing import Optional, List, Dict


class UserManager:
    """
    用户管理器
    负责用户注册、登录验证和密码管理
    """
    
    # 用户数据存储文件
    USERS_FILE = Path("./data/users.json")
    
    def __init__(self):
        """
        初始化用户管理器
        """
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """
        确保用户数据文件存在
        """
        self.USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not self.USERS_FILE.exists():
            self._save_users({})
    
    def _load_users(self) -> Dict[str, dict]:
        """
        加载所有用户数据
        
        Returns:
            Dict[str, dict]: 用户数据字典，key 为用户名
        """
        try:
            with open(self.USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_users(self, users: Dict[str, dict]):
        """
        保存用户数据
        
        Args:
            users: 用户数据字典
        """
        with open(self.USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    
    def _hash_password(self, password: str) -> str:
        """
        对密码进行哈希处理
        
        Args:
            password: 原始密码
            
        Returns:
            str: 哈希后的密码
        """
        # 使用 SHA256 哈希，添加固定盐值
        salt = "vidinsight_salt_2026"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def _sanitize_username(self, username: str) -> str:
        """
        清理用户名
        
        Args:
            username: 原始用户名
            
        Returns:
            str: 清理后的用户名
        """
        # 移除首尾空格
        return username.strip()
    
    def user_exists(self, username: str) -> bool:
        """
        检查用户名是否已存在
        
        Args:
            username: 用户名
            
        Returns:
            bool: 用户是否存在
        """
        username = self._sanitize_username(username)
        users = self._load_users()
        return username in users
    
    def register(self, username: str, password: str) -> tuple:
        """
        注册新用户
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            tuple: (是否成功, 错误消息)
        """
        username = self._sanitize_username(username)
        
        # 验证用户名
        if not username:
            return False, "用户名不能为空"
        
        if len(username) < 2:
            return False, "用户名至少需要2个字符"
        
        if len(username) > 20:
            return False, "用户名不能超过20个字符"
        
        # 验证密码
        if not password:
            return False, "密码不能为空"
        
        if len(password) < 4:
            return False, "密码至少需要4个字符"
        
        # 检查用户名是否已存在
        if self.user_exists(username):
            return False, "用户名已被使用，请选择其他用户名"
        
        # 创建用户
        users = self._load_users()
        users[username] = {
            'password_hash': self._hash_password(password),
            'created_at': __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save_users(users)
        
        return True, "注册成功"
    
    def login(self, username: str, password: str) -> tuple:
        """
        用户登录验证
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            tuple: (是否成功, 错误消息)
        """
        username = self._sanitize_username(username)
        
        if not username or not password:
            return False, "请输入用户名和密码"
        
        users = self._load_users()
        
        if username not in users:
            return False, "用户名不存在"
        
        # 验证密码
        if users[username]['password_hash'] != self._hash_password(password):
            return False, "密码错误"
        
        return True, "登录成功"
    
    def get_all_usernames(self) -> List[str]:
        """
        获取所有已注册的用户名
        
        Returns:
            List[str]: 用户名列表
        """
        users = self._load_users()
        return sorted(users.keys())
    
    def change_password(self, username: str, old_password: str, new_password: str) -> tuple:
        """
        修改密码
        
        Args:
            username: 用户名
            old_password: 旧密码
            new_password: 新密码
            
        Returns:
            tuple: (是否成功, 消息)
        """
        username = self._sanitize_username(username)
        
        # 先验证旧密码
        success, msg = self.login(username, old_password)
        if not success:
            return False, "原密码错误"
        
        # 验证新密码
        if len(new_password) < 4:
            return False, "新密码至少需要4个字符"
        
        # 更新密码
        users = self._load_users()
        users[username]['password_hash'] = self._hash_password(new_password)
        self._save_users(users)
        
        return True, "密码修改成功"
    
    def create_session(self, username: str) -> str:
        """
        创建用户会话
        
        Args:
            username: 用户名
            
        Returns:
            str: 会话 Token
        """
        import secrets
        from datetime import datetime, timedelta
        
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        
        users = self._load_users()
        if username in users:
            users[username]['session_token'] = token
            users[username]['token_expires_at'] = expires_at
            self._save_users(users)
            return token
        return ""
    
    def validate_session(self, token: str) -> Optional[str]:
        """
        验证会话 Token
        
        Args:
            token: 会话 Token
            
        Returns:
            Optional[str]: 有效则返回用户名，否则返回 None
        """
        if not token:
            return None
            
        from datetime import datetime
        
        users = self._load_users()
        for username, data in users.items():
            if data.get('session_token') == token:
                expires_at = data.get('token_expires_at')
                if expires_at and datetime.now().strftime("%Y-%m-%d %H:%M:%S") < expires_at:
                    return username
        return None
    
    def revoke_session(self, username: str):
        """
        撤销用户会话
        
        Args:
            username: 用户名
        """
        users = self._load_users()
        if username in users:
            if 'session_token' in users[username]:
                del users[username]['session_token']
            if 'token_expires_at' in users[username]:
                del users[username]['token_expires_at']
            self._save_users(users)
    
    def is_admin(self, username: str) -> bool:
        """
        检查用户是否为管理员
        
        管理员用户名列表从环境变量 ADMIN_USERS 读取，
        多个用户名用逗号分隔，例如: ADMIN_USERS=admin,zhoujunyu
        
        Args:
            username: 用户名
            
        Returns:
            bool: 是否为管理员
        """
        admin_users_str = os.getenv('ADMIN_USERS', 'admin')
        admin_users = [u.strip() for u in admin_users_str.split(',') if u.strip()]
        return username in admin_users


# 全局用户管理器实例
user_manager = UserManager()
