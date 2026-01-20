"""
标题: HistoryManager
说明: 基于用户名的服务端历史记录管理器（支持分组）
时间: 2026-01-14
@author: zhoujunyu
"""

import json
import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any


class HistoryManager:
    """
    历史记录管理器
    基于用户名在服务端存储历史记录，实现用户隔离
    支持按BV号自动分组
    """
    
    # 历史记录存储目录
    HISTORY_DIR = Path("./data/users")
    
    # 最大保存记录数
    MAX_RECORDS = 100
    
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
    
    def _load_data(self) -> Dict[str, Any]:
        """
        加载用户的历史数据
        
        Returns:
            Dict: 包含 folders 和 records 的数据字典
        """
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 兼容旧格式（纯列表）
                    if isinstance(data, list):
                        return {'folders': [], 'records': data}
                    return data
            return {'folders': [], 'records': []}
        except (json.JSONDecodeError, FileNotFoundError):
            return {'folders': [], 'records': []}
    
    def _save_data(self, data: Dict[str, Any]):
        """
        保存历史数据到文件
        
        Args:
            data: 包含 folders 和 records 的数据字典
        """
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(data, ensure_ascii=False, indent=2, fp=f)
    
    def _generate_folder_id(self) -> str:
        """
        生成唯一的包ID
        
        Returns:
            str: 唯一的包ID
        """
        return f"folder_{uuid.uuid4().hex[:8]}"
    
    # ==================== 包管理 ====================
    
    def create_folder(self, name: str, bv_id: str = None) -> str:
        """
        创建新的包
        
        Args:
            name: 包名称
            bv_id: 关联的BV号（可选）
            
        Returns:
            str: 新创建的包ID
        """
        data = self._load_data()
        folder_id = self._generate_folder_id()
        
        folder = {
            'id': folder_id,
            'name': name,
            'bv_id': bv_id,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        data['folders'].insert(0, folder)
        self._save_data(data)
        return folder_id
    
    def get_all_folders(self) -> List[Dict[str, Any]]:
        """
        获取所有包
        
        Returns:
            List[Dict]: 包列表
        """
        data = self._load_data()
        return data.get('folders', [])
    
    def get_folder_by_bv_id(self, bv_id: str) -> Optional[Dict[str, Any]]:
        """
        根据BV号获取关联的包
        
        Args:
            bv_id: BV号
            
        Returns:
            Optional[Dict]: 包信息，不存在则返回 None
        """
        data = self._load_data()
        for folder in data.get('folders', []):
            if folder.get('bv_id') == bv_id:
                return folder
        return None
    
    def rename_folder(self, folder_id: str, new_name: str) -> bool:
        """
        重命名包
        
        Args:
            folder_id: 包ID
            new_name: 新名称
            
        Returns:
            bool: 是否成功
        """
        try:
            data = self._load_data()
            for folder in data.get('folders', []):
                if folder.get('id') == folder_id:
                    folder['name'] = new_name
                    self._save_data(data)
                    return True
            return False
        except Exception:
            return False
    
    def delete_folder(self, folder_id: str, delete_records: bool = False) -> bool:
        """
        删除包
        
        Args:
            folder_id: 包ID
            delete_records: 是否同时删除包内的记录
            
        Returns:
            bool: 是否成功
        """
        try:
            data = self._load_data()
            
            # 删除包
            data['folders'] = [f for f in data.get('folders', []) if f.get('id') != folder_id]
            
            if delete_records:
                # 删除包内所有记录
                data['records'] = [r for r in data.get('records', []) if r.get('folder_id') != folder_id]
            else:
                # 将记录移出包（设为无包）
                for record in data.get('records', []):
                    if record.get('folder_id') == folder_id:
                        record['folder_id'] = None
            
            self._save_data(data)
            return True
        except Exception:
            return False
    
    def get_folder_records(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        获取包内的所有记录
        
        Args:
            folder_id: 包ID
            
        Returns:
            List[Dict]: 记录列表
        """
        data = self._load_data()
        return [r for r in data.get('records', []) if r.get('folder_id') == folder_id]
    
    def move_record_to_folder(self, video_id: str, folder_id: str) -> bool:
        """
        将记录移动到指定包
        
        Args:
            video_id: 视频ID
            folder_id: 目标包ID（None 表示移出所有包）
            
        Returns:
            bool: 是否成功
        """
        try:
            data = self._load_data()
            for record in data.get('records', []):
                if record.get('video_id') == video_id:
                    record['folder_id'] = folder_id
                    self._save_data(data)
                    return True
            return False
        except Exception:
            return False
    
    # ==================== 记录管理 ====================
    
    def add_record(self, record: Dict[str, Any]) -> bool:
        """
        添加新的历史记录
        自动按BV号归入对应的包（如果包不存在则创建）
        
        Args:
            record: 历史记录字典，需包含 video_id, bv_id, part 等字段
            
        Returns:
            bool: 是否添加成功
        """
        try:
            data = self._load_data()
            
            # 添加时间戳
            if 'created_at' not in record:
                record['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record['username'] = self.username
            
            video_id = record.get('video_id')
            bv_id = record.get('bv_id')
            
            # 自动分组：检查是否有同BV号的包
            if bv_id:
                folder = self.get_folder_by_bv_id(bv_id)
                if folder:
                    record['folder_id'] = folder['id']
                else:
                    # 检查是否已有同BV号的其他分P记录
                    existing_same_bv = [r for r in data.get('records', []) 
                                        if r.get('bv_id') == bv_id and r.get('video_id') != video_id]
                    if existing_same_bv:
                        # 有其他同BV号记录，创建新包
                        # 使用第一个（最早的）记录的标题作为文件夹名
                        first_record = existing_same_bv[-1]  # 列表是按时间倒序的，最后一个是最早的
                        first_title = first_record.get('title', bv_id)
                        # 清理标题（移除"正在分析中..."等占位文本）
                        if '正在分析' in first_title:
                            first_title = bv_id
                        folder_name = first_title[:30] if len(first_title) > 30 else first_title
                        folder_id = self.create_folder(f"📁 {folder_name}", bv_id)
                        record['folder_id'] = folder_id
                        # 将已有的同BV号记录也移入此包
                        data = self._load_data()  # 重新加载（因为create_folder会保存）
                        for r in data.get('records', []):
                            if r.get('bv_id') == bv_id:
                                r['folder_id'] = folder_id
            
            # 检查是否已存在相同视频 ID 的记录
            existing_index = None
            for i, r in enumerate(data.get('records', [])):
                if r.get('video_id') == video_id:
                    existing_index = i
                    break
            
            if existing_index is not None:
                # 保留原有的 folder_id
                if 'folder_id' not in record:
                    record['folder_id'] = data['records'][existing_index].get('folder_id')
                data['records'][existing_index] = record
            else:
                data['records'].insert(0, record)
            
            # 限制记录数量
            if len(data['records']) > self.MAX_RECORDS:
                data['records'] = data['records'][:self.MAX_RECORDS]
            
            self._save_data(data)
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
            data = self._load_data()
            for i, r in enumerate(data.get('records', [])):
                if r.get('video_id') == video_id:
                    data['records'][i].update(updates)
                    self._save_data(data)
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
        data = self._load_data()
        return data.get('records', [])
    
    def get_ungrouped_records(self) -> List[Dict[str, Any]]:
        """
        获取未分组的记录
        
        Returns:
            List[Dict]: 未分组的记录列表
        """
        data = self._load_data()
        return [r for r in data.get('records', []) if not r.get('folder_id')]
    
    def get_grouped_history(self) -> Dict[str, Any]:
        """
        获取分组后的历史记录结构
        
        Returns:
            Dict: {
                'folders': [
                    {'id': ..., 'name': ..., 'records': [...]}
                ],
                'ungrouped': [...]  # 未分组的记录
            }
        """
        data = self._load_data()
        folders = data.get('folders', [])
        records = data.get('records', [])
        
        result = {
            'folders': [],
            'ungrouped': []
        }
        
        # 按包分组
        folder_records = {}
        for record in records:
            folder_id = record.get('folder_id')
            if folder_id:
                if folder_id not in folder_records:
                    folder_records[folder_id] = []
                folder_records[folder_id].append(record)
            else:
                result['ungrouped'].append(record)
        
        # 构建包结构
        for folder in folders:
            folder_info = folder.copy()
            folder_info['records'] = folder_records.get(folder['id'], [])
            result['folders'].append(folder_info)
        
        return result
    
    def get_record_by_video_id(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        根据视频 ID 获取历史记录
        
        Args:
            video_id: 视频 ID
            
        Returns:
            Optional[Dict]: 历史记录，不存在则返回 None
        """
        data = self._load_data()
        for r in data.get('records', []):
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
            data = self._load_data()
            data['records'] = [r for r in data.get('records', []) if r.get('video_id') != video_id]
            self._save_data(data)
            return True
        except Exception:
            return False
    
    def clear_all(self) -> bool:
        """
        清空所有历史记录和包
        
        Returns:
            bool: 是否清空成功
        """
        try:
            self._save_data({'folders': [], 'records': []})
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
            data = self._load_data()
            existing_ids = set(r.get('video_id') for r in data.get('records', []))
            
            new_count = 0
            for record in records:
                if isinstance(record, dict) and record.get('video_id') not in existing_ids:
                    record['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    record['username'] = self.username
                    data['records'].insert(0, record)
                    existing_ids.add(record.get('video_id'))
                    new_count += 1
            
            # 限制数量
            if len(data['records']) > self.MAX_RECORDS:
                data['records'] = data['records'][:self.MAX_RECORDS]
            
            self._save_data(data)
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

