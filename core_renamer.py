"""
批量文件重命名工具 - 重命名规则核心模块

本模块负责：
- 定义重命名规则数据结构
- 解析和应用各种重命名规则
- 生成新文件名

支持的重命名规则：
- 添加前缀/后缀
- 字符串替换
- 序号递增
- 日期插入
- 正则替换

强约束：
- 源文件目录（只读）：./source_data/
- 输出目录（只写）：./output_build/
- 严禁修改 .do_not_touch.cfg
"""

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple, List

from utils.config import DEFAULT_NUMBER_START, DEFAULT_PADDING, DEFAULT_DATE_FORMAT
from utils.helpers import split_filename, get_file_modification_time, format_date_for_filename, safe_filename
from utils.validators import parse_replace_string, parse_regex_replace


@dataclass
class RenameRule:
    """
    重命名规则数据类
    
    Attributes:
        prefix: 前缀字符串
        suffix: 后缀字符串（在扩展名前）
        replace: 替换字符串 "old,new"
        number_start: 序号起始值
        padding: 序号补零位数
        date_format: 日期格式字符串
        regex: 正则替换字符串 "pattern,replacement"
    """
    prefix: str = ""
    suffix: str = ""
    replace: Optional[str] = None
    number_start: int = DEFAULT_NUMBER_START
    padding: int = DEFAULT_PADDING
    date_format: Optional[str] = None
    regex: Optional[str] = None


def apply_prefix(filename: str, prefix: str) -> str:
    """
    应用前缀规则
    
    Args:
        filename: 原始文件名
        prefix: 前缀字符串
        
    Returns:
        添加前缀后的文件名
    """
    if not prefix:
        return filename
    
    name, ext = split_filename(filename)
    return f"{prefix}{name}{ext}"


def apply_suffix(filename: str, suffix: str) -> str:
    """
    应用后缀规则（在扩展名前添加）
    
    Args:
        filename: 原始文件名
        suffix: 后缀字符串
        
    Returns:
        添加后缀后的文件名
    """
    if not suffix:
        return filename
    
    name, ext = split_filename(filename)
    return f"{name}{suffix}{ext}"


def apply_replace(filename: str, replace_string: Optional[str]) -> str:
    """
    应用字符串替换规则
    
    Args:
        filename: 原始文件名
        replace_string: 替换字符串 "old,new"
        
    Returns:
        替换后的文件名
    """
    if not replace_string:
        return filename
    
    result = parse_replace_string(replace_string)
    if result is None or result is False:
        return filename
    
    old_str, new_str = result
    name, ext = split_filename(filename)
    
    # 只在主名中替换，保留扩展名
    new_name = name.replace(old_str, new_str)
    return f"{new_name}{ext}"


def apply_number(filename: str, number: int, padding: int) -> str:
    """
    应用序号规则（将序号插入到文件名开头）
    
    Args:
        filename: 原始文件名
        number: 序号值
        padding: 补零位数
        
    Returns:
        添加序号后的文件名
    """
    name, ext = split_filename(filename)
    number_str = str(number).zfill(padding)
    return f"{number_str}_{name}{ext}"


def apply_date(
    filename: str,
    date_format: Optional[str],
    source_dir: str
) -> str:
    """
    应用日期规则（使用文件修改日期）
    
    Args:
        filename: 原始文件名
        date_format: 日期格式字符串
        source_dir: 源文件目录
        
    Returns:
        添加日期后的文件名
    """
    if not date_format:
        return filename
    
    filepath = os.path.join(source_dir, filename)
    mtime = get_file_modification_time(filepath)
    
    if mtime is None:
        return filename
    
    date_str = format_date_for_filename(mtime, date_format)
    if not date_str:
        return filename
    
    name, ext = split_filename(filename)
    return f"{name}_{date_str}{ext}"


def apply_regex(filename: str, regex_string: Optional[str]) -> str:
    """
    应用正则替换规则
    
    Args:
        filename: 原始文件名
        regex_string: 正则替换字符串 "pattern,replacement"
        
    Returns:
        正则替换后的文件名
    """
    if not regex_string:
        return filename
    
    result = parse_regex_replace(regex_string)
    if result is None or result is False:
        return filename
    
    pattern, replacement = result
    name, ext = split_filename(filename)
    
    try:
        # 只在主名中替换，保留扩展名
        new_name = re.sub(pattern, replacement, name)
        return f"{new_name}{ext}"
    except re.error:
        return filename


def generate_new_filename(
    original_filename: str,
    rule: RenameRule,
    sequence_number: Optional[int] = None,
    source_dir: str = ""
) -> str:
    """
    根据规则生成新文件名
    
    应用规则的顺序：
    1. 字符串替换
    2. 正则替换
    3. 添加前缀
    4. 添加后缀
    5. 添加日期
    6. 添加序号
    
    Args:
        original_filename: 原始文件名
        rule: 重命名规则
        sequence_number: 序号（可选）
        source_dir: 源文件目录（用于获取日期）
        
    Returns:
        生成的新文件名
    """
    new_filename = original_filename
    
    # 1. 字符串替换
    if rule.replace:
        new_filename = apply_replace(new_filename, rule.replace)
    
    # 2. 正则替换
    if rule.regex:
        new_filename = apply_regex(new_filename, rule.regex)
    
    # 3. 添加前缀
    if rule.prefix:
        new_filename = apply_prefix(new_filename, rule.prefix)
    
    # 4. 添加后缀
    if rule.suffix:
        new_filename = apply_suffix(new_filename, rule.suffix)
    
    # 5. 添加日期
    if rule.date_format and source_dir:
        new_filename = apply_date(new_filename, rule.date_format, source_dir)
    
    # 6. 添加序号
    if sequence_number is not None:
        new_filename = apply_number(
            new_filename,
            sequence_number,
            rule.padding
        )
    
    # 确保文件名安全
    new_filename = safe_filename(new_filename)
    
    return new_filename


def generate_rename_mapping(
    files: List[str],
    rule: RenameRule,
    source_dir: str
) -> dict:
    """
    为文件列表生成重命名映射
    
    Args:
        files: 文件名列表
        rule: 重命名规则
        source_dir: 源文件目录
        
    Returns:
        {原文件名: 新文件名} 映射字典
    """
    mapping = {}
    current_number = rule.number_start
    
    for filename in files:
        # 检查是否需要序号
        sequence_number = current_number if rule.number_start >= 0 else None
        
        new_filename = generate_new_filename(
            filename,
            rule,
            sequence_number,
            source_dir
        )
        
        mapping[filename] = new_filename
        current_number += 1
    
    return mapping


def preview_rename(
    files: List[str],
    rule: RenameRule,
    source_dir: str
) -> List[Tuple[str, str]]:
    """
    预览重命名结果（返回列表形式）
    
    Args:
        files: 文件名列表
        rule: 重命名规则
        source_dir: 源文件目录
        
    Returns:
        [(原文件名, 新文件名), ...] 列表
    """
    mapping = generate_rename_mapping(files, rule, source_dir)
    return list(mapping.items())


# 用于直接测试
if __name__ == '__main__':
    # 测试各种规则
    test_files = [
        "photo.jpg",
        "document.txt",
        "image_001.png"
    ]
    
    # 测试前缀
    rule1 = RenameRule(prefix="IMG_")
    print("前缀规则:")
    for f in test_files:
        print(f"  {f} -> {generate_new_filename(f, rule1)}")
    
    # 测试后缀
    rule2 = RenameRule(suffix="_2025")
    print("\n后缀规则:")
    for f in test_files:
        print(f"  {f} -> {generate_new_filename(f, rule2)}")
    
    # 测试替换
    rule3 = RenameRule(replace="photo,image")
    print("\n替换规则:")
    for f in test_files:
        print(f"  {f} -> {generate_new_filename(f, rule3)}")
    
    # 测试序号
    rule4 = RenameRule(number_start=1, padding=3)
    print("\n序号规则:")
    for i, f in enumerate(test_files, 1):
        print(f"  {f} -> {generate_new_filename(f, rule4, i)}")
