"""
批量文件重命名工具 - 工具函数模块

本模块提供各种辅助功能：
- 目录操作（创建、检查）
- 文件遍历和排序
- 日志读写（JSON格式）
- 预览表格格式化输出
- 其他通用工具函数

强约束：
- 源文件目录（只读）：./source_data/
- 输出目录（只写）：./output_build/
- 严禁修改 .do_not_touch.cfg
"""

import os
import json
import sys
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple

from utils.config import (
    PREVIEW_TABLE_CONFIG, PROTECTED_FILE, is_protected_file
)


def ensure_dir(path: str) -> bool:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        path: 目录路径
        
    Returns:
        是否成功
    """
    try:
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return os.path.isdir(path) and os.access(path, os.W_OK)
    except OSError:
        return False


def list_files(
    directory: str,
    extensions: Optional[List[str]] = None,
    exclude_protected: bool = True
) -> List[str]:
    """
    列出目录中的文件（不包括子目录）
    
    Args:
        directory: 目标目录
        extensions: 扩展名过滤列表（如 ['.jpg', '.png']），None表示所有
        exclude_protected: 是否排除受保护文件
        
    Returns:
        文件名列表（按字母排序）
    """
    files = []
    
    try:
        if not os.path.exists(directory) or not os.path.isdir(directory):
            return files
        
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            
            # 跳过目录
            if os.path.isdir(item_path):
                continue
            
            # 跳过受保护文件
            if exclude_protected and is_protected_file(item):
                continue
            
            # 扩展名过滤
            if extensions:
                _, ext = os.path.splitext(item)
                if ext.lower() not in [e.lower() for e in extensions]:
                    continue
            
            files.append(item)
        
        # 按字母排序
        files.sort()
        
    except OSError as e:
        print(f"警告：读取目录失败 {directory}: {e}", file=sys.stderr)
    
    return files


def get_file_modification_time(filepath: str) -> Optional[datetime]:
    """
    获取文件修改时间
    
    Args:
        filepath: 文件路径
        
    Returns:
        修改时间，失败返回 None
    """
    try:
        if os.path.exists(filepath):
            mtime = os.path.getmtime(filepath)
            return datetime.fromtimestamp(mtime)
    except OSError:
        pass
    return None


def format_date_for_filename(dt: Optional[datetime], date_format: str) -> str:
    """
    将日期时间格式化为文件名可用的字符串
    
    Args:
        dt: 日期时间对象
        date_format: 日期格式字符串
        
    Returns:
        格式化后的字符串，失败返回空字符串
    """
    if dt is None:
        return ""
    try:
        return dt.strftime(date_format)
    except ValueError:
        return ""


def truncate_string(s: str, max_length: int, suffix: str = "...") -> str:
    """
    截断字符串到指定长度
    
    Args:
        s: 原始字符串
        max_length: 最大长度
        suffix: 截断后缀
        
    Returns:
        截断后的字符串
    """
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def format_preview_table(rename_map: Dict[str, str]) -> str:
    """
    格式化重命名预览表格
    
    Args:
        rename_map: 旧名->新名映射字典
        
    Returns:
        格式化后的表格字符串
    """
    if not rename_map:
        return "没有需要重命名的文件"
    
    cfg = PREVIEW_TABLE_CONFIG
    index_width = cfg['index_width']
    old_name_width = cfg['old_name_width']
    new_name_width = cfg['new_name_width']
    
    lines = []
    
    # 表头分隔线
    total_width = index_width + old_name_width + new_name_width + 6
    lines.append("=" * total_width)
    
    # 表头
    header = (
        f"{'序号':^{index_width}} | "
        f"{'原文件名':^{old_name_width}} | "
        f"{'新文件名':^{new_name_width}}"
    )
    lines.append(header)
    lines.append("-" * total_width)
    
    # 数据行
    for idx, (old_name, new_name) in enumerate(rename_map.items(), 1):
        old_display = truncate_string(old_name, old_name_width)
        new_display = truncate_string(new_name, new_name_width)
        
        row = (
            f"{idx:^{index_width}} | "
            f"{old_display:<{old_name_width}} | "
            f"{new_display:<{new_name_width}}"
        )
        lines.append(row)
    
    # 表尾分隔线
    lines.append("=" * total_width)
    
    return "\n".join(lines)


def save_preview(rename_map: Dict[str, str], filepath: str) -> bool:
    """
    保存预览结果到文本文件
    
    Args:
        rename_map: 旧名->新名映射字典
        filepath: 输出文件路径
        
    Returns:
        是否成功
    """
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(filepath)
        if output_dir and not ensure_dir(output_dir):
            return False
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("批量文件重命名预览\n")
            f.write("=" * 60 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"文件总数: {len(rename_map)}\n")
            f.write("=" * 60 + "\n\n")
            
            if not rename_map:
                f.write("没有需要重命名的文件\n")
                return True
            
            # 写入表头
            f.write(f"{'序号':<6} {'原文件名':<40} {'新文件名':<40}\n")
            f.write("-" * 90 + "\n")
            
            # 写入数据
            for idx, (old_name, new_name) in enumerate(rename_map.items(), 1):
                f.write(f"{idx:<6} {old_name:<40} {new_name:<40}\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("注意：此为预览，实际文件未被修改\n")
        
        return True
        
    except IOError as e:
        print(f"警告：保存预览文件失败: {e}", file=sys.stderr)
        return False


def save_log(results: Dict[str, Any], filepath: str) -> bool:
    """
    保存操作日志到JSON文件
    
    Args:
        results: 操作结果字典 {旧名: {success: bool, new_name: str, error: str}}
        filepath: 输出文件路径
        
    Returns:
        是否成功
    """
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(filepath)
        if output_dir and not ensure_dir(output_dir):
            return False
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'total_count': len(results),
            'success_count': sum(1 for r in results.values() if r.get('success', False)),
            'fail_count': sum(1 for r in results.values() if not r.get('success', False)),
            'operations': results
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        return True
        
    except (IOError, TypeError) as e:
        print(f"警告：保存日志文件失败: {e}", file=sys.stderr)
        return False


def load_log(filepath: str) -> Optional[Dict[str, Any]]:
    """
    从JSON文件加载操作日志
    
    Args:
        filepath: 日志文件路径
        
    Returns:
        日志数据字典，失败返回 None
    """
    try:
        if not os.path.exists(filepath):
            print(f"错误：日志文件不存在: {filepath}", file=sys.stderr)
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 验证基本结构
        if not isinstance(data, dict):
            print(f"错误：日志文件格式不正确", file=sys.stderr)
            return None
        
        if 'operations' not in data:
            print(f"错误：日志文件缺少操作记录", file=sys.stderr)
            return None
        
        return data['operations']
        
    except json.JSONDecodeError as e:
        print(f"错误：日志文件JSON格式错误: {e}", file=sys.stderr)
        return None
    except IOError as e:
        print(f"错误：读取日志文件失败: {e}", file=sys.stderr)
        return None


def split_filename(filename: str) -> Tuple[str, str]:
    """
    分割文件名为（主名，扩展名）
    
    Args:
        filename: 文件名
        
    Returns:
        (主名, 扩展名) 元组
    """
    name, ext = os.path.splitext(filename)
    return name, ext


def safe_filename(filename: str) -> str:
    """
    将文件名中的非法字符替换为安全字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        安全的文件名
    """
    # Windows 非法字符: < > : " / \ | ? *
    illegal_chars = '<>:"/\\|?*'
    result = filename
    for char in illegal_chars:
        result = result.replace(char, '_')
    
    # 去除首尾空格和点
    result = result.strip(' .')
    
    # 如果结果为空，返回默认名
    if not result:
        result = "unnamed"
    
    return result


def natural_sort_key(filename: str) -> List:
    """
    自然排序键函数（处理数字）
    
    Args:
        filename: 文件名
        
    Returns:
        排序键列表
    """
    import re
    return [int(text) if text.isdigit() else text.lower() 
            for text in re.split(r'(\d+)', filename)]


def sort_files_natural(files: List[str]) -> List[str]:
    """
    对文件列表进行自然排序
    
    Args:
        files: 文件名列表
        
    Returns:
        排序后的列表
    """
    return sorted(files, key=natural_sort_key)
