"""
批量文件重命名工具 - 重命名引擎模块

本模块负责：
- 扫描和获取源目录文件列表
- 生成重命名映射
- 检测命名冲突
- 执行实际的重命名操作（os.rename）
- 处理撤销操作

强约束：
- 源文件目录（只读）：./source_data/
- 输出目录（只写）：./output_build/
- 严禁修改 .do_not_touch.cfg
"""

import os
import sys
from typing import List, Dict, Optional, Any

from core_renamer import RenameRule, generate_rename_mapping
from utils.config import SOURCE_DIR, PROTECTED_FILE, is_protected_file
from utils.helpers import list_files
from utils.validators import is_protected_file as validate_protected_file


class RenameEngine:
    """
    重命名引擎类
    
    负责管理文件重命名的完整流程：
    - 文件扫描
    - 映射生成
    - 冲突检测
    - 执行重命名
    """
    
    def __init__(self, source_dir: str = SOURCE_DIR):
        """
        初始化重命名引擎
        
        Args:
            source_dir: 源文件目录路径
        """
        self.source_dir = os.path.normpath(source_dir)
        self.errors: List[str] = []
    
    def get_files(self, extensions: Optional[List[str]] = None) -> List[str]:
        """
        获取源目录中的文件列表
        
        Args:
            extensions: 扩展名过滤列表，None 表示所有文件
            
        Returns:
            文件名列表（按字母排序）
        """
        return list_files(self.source_dir, extensions, exclude_protected=True)
    
    def generate_rename_map(
        self,
        files: List[str],
        rule: RenameRule
    ) -> Dict[str, str]:
        """
        生成重命名映射
        
        Args:
            files: 文件名列表
            rule: 重命名规则
            
        Returns:
            {原文件名: 新文件名} 映射字典
        """
        if not files:
            return {}
        
        return generate_rename_mapping(files, rule, self.source_dir)
    
    def check_conflicts(self, rename_map: Dict[str, str]) -> Dict[str, List[str]]:
        """
        检查重命名映射中的命名冲突
        
        冲突情况：
        1. 多个原文件映射到同一个新文件名
        2. 新文件名与现有文件冲突（非本次重命名的文件）
        
        Args:
            rename_map: 重命名映射
            
        Returns:
            {新文件名: [原文件名列表]} 冲突字典，空表示无冲突
        """
        conflicts: Dict[str, List[str]] = {}
        
        # 检查1：多个原文件映射到同一个新文件名
        new_name_to_old: Dict[str, List[str]] = {}
        for old_name, new_name in rename_map.items():
            if new_name not in new_name_to_old:
                new_name_to_old[new_name] = []
            new_name_to_old[new_name].append(old_name)
        
        for new_name, old_names in new_name_to_old.items():
            if len(old_names) > 1:
                conflicts[new_name] = old_names
        
        # 检查2：新文件名与现有文件冲突
        for old_name, new_name in rename_map.items():
            # 跳过不变的情况
            if old_name == new_name:
                continue
            
            new_path = os.path.join(self.source_dir, new_name)
            
            # 如果新文件名已存在且不在重命名映射中
            if os.path.exists(new_path):
                # 检查是否是本次重命名的目标文件
                if new_name not in rename_map:
                    if new_name not in conflicts:
                        conflicts[new_name] = []
                    conflicts[new_name].append(f"[已存在文件] {new_name}")
        
        return conflicts
    
    def apply_rename(
        self,
        rename_map: Dict[str, str],
        undo_mode: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        执行重命名操作
        
        Args:
            rename_map: 重命名映射 {原文件名: 新文件名}
            undo_mode: 是否为撤销模式（True 时不检查目标文件是否存在）
            
        Returns:
            操作结果字典 {
                原文件名: {
                    'success': bool,
                    'new_name': str,
                    'error': str (可选)
                }
            }
        """
        results: Dict[str, Dict[str, Any]] = {}
        
        for old_name, new_name in rename_map.items():
            result = self._rename_single_file(old_name, new_name, undo_mode)
            results[old_name] = result
        
        return results
    
    def _rename_single_file(
        self,
        old_name: str,
        new_name: str,
        undo_mode: bool = False
    ) -> Dict[str, Any]:
        """
        重命名单个文件
        
        Args:
            old_name: 原文件名
            new_name: 新文件名
            undo_mode: 是否为撤销模式
            
        Returns:
            操作结果字典
        """
        result = {
            'success': False,
            'new_name': new_name,
            'error': None
        }
        
        old_path = os.path.join(self.source_dir, old_name)
        new_path = os.path.join(self.source_dir, new_name)
        
        # 检查原文件是否存在
        if not os.path.exists(old_path):
            result['error'] = f"原文件不存在: {old_name}"
            return result
        
        # 检查是否是受保护文件
        if is_protected_file(old_name):
            result['error'] = f"禁止操作受保护文件: {old_name}"
            return result
        
        # 如果新旧名称相同，跳过
        if old_name == new_name:
            result['success'] = True
            result['error'] = "文件名未改变"
            return result
        
        # 检查目标文件是否已存在（非撤销模式）
        if not undo_mode and os.path.exists(new_path):
            result['error'] = f"目标文件已存在: {new_name}"
            return result
        
        # 执行重命名
        try:
            os.rename(old_path, new_path)
            result['success'] = True
        except PermissionError:
            result['error'] = f"权限不足: {old_name}"
        except OSError as e:
            result['error'] = f"重命名失败: {e}"
        
        return result
    
    def preview_rename(
        self,
        files: List[str],
        rule: RenameRule
    ) -> Dict[str, str]:
        """
        预览重命名结果
        
        Args:
            files: 文件名列表
            rule: 重命名规则
            
        Returns:
            重命名映射
        """
        return self.generate_rename_map(files, rule)
    
    def get_stats(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
        """
        获取操作统计信息
        
        Args:
            results: 操作结果字典
            
        Returns:
            统计字典
        """
        total = len(results)
        success = sum(1 for r in results.values() if r.get('success', False))
        failed = total - success
        
        return {
            'total': total,
            'success': success,
            'failed': failed
        }


def check_file_exists(filepath: str) -> bool:
    """
    检查文件是否存在
    
    Args:
        filepath: 文件路径
        
    Returns:
        是否存在
    """
    return os.path.exists(filepath) and os.path.isfile(filepath)


def check_directory_writable(directory: str) -> bool:
    """
    检查目录是否可写
    
    Args:
        directory: 目录路径
        
    Returns:
        是否可写
    """
    if not os.path.exists(directory):
        return False
    if not os.path.isdir(directory):
        return False
    return os.access(directory, os.W_OK)


# 用于直接测试
if __name__ == '__main__':
    # 创建测试引擎
    engine = RenameEngine()
    
    # 获取文件列表
    files = engine.get_files()
    print(f"找到 {len(files)} 个文件:")
    for f in files:
        print(f"  - {f}")
    
    if files:
        # 测试重命名规则
        rule = RenameRule(prefix="TEST_", number_start=1, padding=3)
        rename_map = engine.generate_rename_map(files, rule)
        
        print("\n重命名预览:")
        for old, new in rename_map.items():
            print(f"  {old} -> {new}")
        
        # 检查冲突
        conflicts = engine.check_conflicts(rename_map)
        if conflicts:
            print("\n检测到冲突:")
            for new_name, old_names in conflicts.items():
                print(f"  {new_name}: {old_names}")
        else:
            print("\n无冲突")
