"""
标题: HistoryManager
说明: 基于用户名的服务端历史记录管理器
时间: 2026-01-14
@author: zhoujunyu
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any


class HistoryManager:
    """
    历史记录管理器
    基于用户名在服务端存储历史记录，实现用户隔离
    """
    
    # 历史记录存储目录
    HISTORY_DIR = Path("./data/users")
    
    # 最大保存记录数
    MAX_RECORDS = 50
    
    def __init__(self, username: str):
        """
        初始化历史记录管理器
        
        Args:
            username: 用户名，用于隔离不同用户的数据
        """
        self.username = self._sanitize_username(username)
        self.history_file = self.HISTORY_DIR / f"{self.username}.json"
        self._ensure_dir_exists()
    
    def _sanitize_username(self, username: str) -> str:
        """
        清理用户名，移除非法字符
        
        Args:
            username: 原始用户名
            
        Returns:
            str: 清理后的安全用户名
        """
        # 只保留中文、字母、数字、下划线
        sanitized = re.sub(r'[^\w\u4e00-\u9fff]', '_', username)
        return sanitized[:50] if len(sanitized) > 50 else sanitized
    
    def _ensure_dir_exists(self):
        """
        确保存储目录存在
        """
        self.HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_records(self) -> List[Dict[str, Any]]:
        """
        加载用户的历史记录
        
        Returns:
            List[Dict]: 历史记录列表
        """
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_records(self, records: List[Dict[str, Any]]):
        """
        保存历史记录到文件
        
        Args:
            records: 历史记录列表
        """
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    
    def add_record(self, record: Dict[str, Any]) -> bool:
        """
        添加新的历史记录
        
        Args:
            record: 历史记录字典
            
        Returns:
            bool: 是否添加成功
        """
        try:
            records = self._load_records()
            
            # 添加时间戳
            if 'created_at' not in record:
                record['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record['username'] = self.username
            
            # 检查是否已存在相同视频 ID 的记录
            video_id = record.get('video_id')
            existing_index = None
            for i, r in enumerate(records):
                if r.get('video_id') == video_id:
                    existing_index = i
                    break
            
            if existing_index is not None:
                records[existing_index] = record
            else:
                records.insert(0, record)
            
            # 限制记录数量
            if len(records) > self.MAX_RECORDS:
                records = records[:self.MAX_RECORDS]
            
            self._save_records(records)
            return True
            
        except Exception:
            return False

    def update_record(self, video_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新现有记录
        
        Args:
            video_id: 视频 ID
            updates: 要更新的字段字典
            
        Returns:
            bool: 是否更新成功
        """
        try:
            records = self._load_records()
            for i, r in enumerate(records):
                if r.get('video_id') == video_id:
                    records[i].update(updates)
                    self._save_records(records)
                    return True
            return False
        except Exception:
            return False
    
    def get_all_records(self) -> List[Dict[str, Any]]:
        """
        获取所有历史记录
        
        Returns:
            List[Dict]: 历史记录列表
        """
        return self._load_records()
    
    def get_record_by_video_id(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        根据视频 ID 获取历史记录
        
        Args:
            video_id: 视频 ID
            
        Returns:
            Optional[Dict]: 历史记录，不存在则返回 None
        """
        records = self._load_records()
        for r in records:
            if r.get('video_id') == video_id:
                return r
        return None
    
    def delete_record(self, video_id: str) -> bool:
        """
        删除指定视频的历史记录
        
        Args:
            video_id: 视频 ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            records = self._load_records()
            records = [r for r in records if r.get('video_id') != video_id]
            self._save_records(records)
            return True
        except Exception:
            return False
    
    def clear_all(self) -> bool:
        """
        清空所有历史记录
        
        Returns:
            bool: 是否清空成功
        """
        try:
            self._save_records([])
            return True
        except Exception:
            return False
    
    def import_records(self, records: List[Dict[str, Any]]) -> int:
        """
        导入历史记录
        
        Args:
            records: 要导入的记录列表
            
        Returns:
            int: 成功导入的记录数
        """
        try:
            existing_records = self._load_records()
            existing_ids = set(r.get('video_id') for r in existing_records)
            
            new_count = 0
            for record in records:
                if isinstance(record, dict) and record.get('video_id') not in existing_ids:
                    record['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    record['username'] = self.username
                    existing_records.insert(0, record)
                    existing_ids.add(record.get('video_id'))
                    new_count += 1
            
            # 限制数量
            if len(existing_records) > self.MAX_RECORDS:
                existing_records = existing_records[:self.MAX_RECORDS]
            
            self._save_records(existing_records)
            return new_count
            
        except Exception:
            return 0
    
    @staticmethod
    def get_all_users() -> List[str]:
        """
        获取所有已注册的用户名
        
        Returns:
            List[str]: 用户名列表
        """
        history_dir = HistoryManager.HISTORY_DIR
        if not history_dir.exists():
            return []
        
        users = []
        for file in history_dir.glob("*.json"):
            users.append(file.stem)
        return sorted(users)
