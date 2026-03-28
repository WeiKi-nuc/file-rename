"""
批量文件重命名工具 - 输入校验模块

本模块提供所有输入数据的校验功能：
- 路径存在性和权限校验
- 扩展名格式校验
- 日期格式校验
- 正则表达式合法性校验
- 替换字符串格式校验

强约束：
- 源文件目录（只读）：./source_data/
- 输出目录（只写）：./output_build/
- 严禁修改 .do_not_touch.cfg
"""

import os
import re
from datetime import datetime
from typing import List, Optional, Tuple, Union

from utils.config import (
    SOURCE_DIR, OUTPUT_DIR, PROTECTED_FILE,
    SUPPORTED_DATE_FORMATS, PROTECTED_EXTENSIONS,
    ERROR_MESSAGES
)


def validate_source_dir(path: str) -> bool:
    """
    验证源目录是否存在且可读
    
    Args:
        path: 目录路径
        
    Returns:
        验证是否通过
    """
    normalized_path = os.path.normpath(path)
    
    if not os.path.exists(normalized_path):
        print(ERROR_MESSAGES['source_dir_not_exist'].format(path), file=__import__('sys').stderr)
        return False
    
    if not os.path.isdir(normalized_path):
        print(ERROR_MESSAGES['source_dir_not_exist'].format(path), file=__import__('sys').stderr)
        return False
    
    if not os.access(normalized_path, os.R_OK):
        print(ERROR_MESSAGES['source_dir_not_readable'].format(path), file=__import__('sys').stderr)
        return False
    
    return True


def validate_output_dir(path: str) -> bool:
    """
    验证输出目录是否可写（如果不存在则尝试创建）
    
    Args:
        path: 目录路径
        
    Returns:
        验证是否通过
    """
    normalized_path = os.path.normpath(path)
    
    if os.path.exists(normalized_path):
        if not os.path.isdir(normalized_path):
            print(ERROR_MESSAGES['output_dir_create_failed'].format(f"{path} 不是目录"), file=__import__('sys').stderr)
            return False
        if not os.access(normalized_path, os.W_OK):
            print(ERROR_MESSAGES['output_dir_create_failed'].format(f"{path} 不可写"), file=__import__('sys').stderr)
            return False
        return True
    
    # 目录不存在，尝试创建
    try:
        os.makedirs(normalized_path, exist_ok=True)
        return True
    except OSError as e:
        print(ERROR_MESSAGES['output_dir_create_failed'].format(f"{path}: {e}"), file=__import__('sys').stderr)
        return False


def validate_extensions(ext_string: Optional[str]) -> Optional[List[str]]:
    """
    验证扩展名字符串并返回扩展名列表
    
    Args:
        ext_string: 逗号分隔的扩展名字符串，如 "jpg,png,txt"
        
    Returns:
        扩展名列表（带.前缀），None 表示所有文件
    """
    if not ext_string:
        return None
    
    if not isinstance(ext_string, str):
        print(ERROR_MESSAGES['invalid_extension'].format(ext_string), file=__import__('sys').stderr)
        return None
    
    extensions = []
    for ext in ext_string.split(','):
        ext = ext.strip().lower()
        if not ext:
            continue
        
        # 确保扩展名以.开头
        if not ext.startswith('.'):
            ext = '.' + ext
        
        # 检查是否受保护
        if ext in PROTECTED_EXTENSIONS:
            print(f"警告：跳过受保护的扩展名: {ext}", file=__import__('sys').stderr)
            continue
        
        # 验证扩展名格式（只允许字母数字）
        ext_name = ext[1:]  # 去掉.
        if not re.match(r'^[a-zA-Z0-9]+$', ext_name):
            print(ERROR_MESSAGES['invalid_extension'].format(ext), file=__import__('sys').stderr)
            return None
        
        extensions.append(ext)
    
    return extensions if extensions else None


def validate_date_format(date_format: Optional[str]) -> bool:
    """
    验证日期格式字符串是否合法
    
    Args:
        date_format: 日期格式字符串，如 "%Y%m%d"
        
    Returns:
        验证是否通过
    """
    if not date_format:
        return True
    
    if not isinstance(date_format, str):
        print(ERROR_MESSAGES['invalid_date_format'].format(date_format), file=__import__('sys').stderr)
        return False
    
    # 尝试用当前时间格式化测试
    try:
        datetime.now().strftime(date_format)
        return True
    except ValueError as e:
        print(ERROR_MESSAGES['invalid_date_format'].format(f"{date_format}: {e}"), file=__import__('sys').stderr)
        return False


def validate_regex(pattern: Optional[str]) -> bool:
    """
    验证正则表达式是否合法
    
    Args:
        pattern: 正则表达式字符串
        
    Returns:
        验证是否通过
    """
    if not pattern:
        return True
    
    if not isinstance(pattern, str):
        print(ERROR_MESSAGES['invalid_regex'].format(pattern), file=__import__('sys').stderr)
        return False
    
    try:
        re.compile(pattern)
        return True
    except re.error as e:
        print(ERROR_MESSAGES['invalid_regex'].format(f"{pattern}: {e}"), file=__import__('sys').stderr)
        return False


def parse_replace_string(replace_string: Optional[str]) -> Union[Tuple[str, str], None, bool]:
    """
    解析替换字符串格式 "old,new"
    
    Args:
        replace_string: 替换字符串，如 "old,new"
        
    Returns:
        (old_str, new_str) 元组，None 表示空输入，False 表示格式错误
    """
    if not replace_string:
        return None
    
    if not isinstance(replace_string, str):
        print(f"错误：替换字符串必须是字符串类型", file=__import__('sys').stderr)
        return False
    
    # 查找逗号分隔符（只取第一个逗号）
    parts = replace_string.split(',', 1)
    if len(parts) != 2:
        print(f"错误：替换字符串格式错误，应为 'old,new'，实际: {replace_string}", file=__import__('sys').stderr)
        return False
    
    old_str, new_str = parts[0], parts[1]
    return (old_str, new_str)


def parse_regex_replace(regex_string: Optional[str]) -> Union[Tuple[str, str], None, bool]:
    """
    解析正则替换字符串格式 "pattern,replacement"
    
    Args:
        regex_string: 正则替换字符串，如 "pattern,replacement"
        
    Returns:
        (pattern, replacement) 元组，None 表示空输入，False 表示格式错误或正则无效
    """
    if not regex_string:
        return None
    
    if not isinstance(regex_string, str):
        print(f"错误：正则替换字符串必须是字符串类型", file=__import__('sys').stderr)
        return False
    
    # 查找逗号分隔符（只取第一个逗号）
    parts = regex_string.split(',', 1)
    if len(parts) != 2:
        print(f"错误：正则替换字符串格式错误，应为 'pattern,replacement'，实际: {regex_string}", file=__import__('sys').stderr)
        return False
    
    pattern, replacement = parts[0], parts[1]
    
    # 验证正则表达式
    if not validate_regex(pattern):
        return False
    
    return (pattern, replacement)


def validate_number_start(number_start: Optional[Union[int, str]]) -> int:
    """
    验证序号起始值
    
    Args:
        number_start: 序号起始值
        
    Returns:
        验证后的整数，验证失败返回 1
    """
    if number_start is None:
        return 1
    
    try:
        num = int(number_start)
        if num < 0:
            print(f"警告：序号起始值不能为负数，使用默认值 1", file=__import__('sys').stderr)
            return 1
        return num
    except (ValueError, TypeError):
        print(f"警告：序号起始值无效，使用默认值 1", file=__import__('sys').stderr)
        return 1


def validate_padding(padding: Optional[Union[int, str]]) -> int:
    """
    验证序号补零位数
    
    Args:
        padding: 补零位数
        
    Returns:
        验证后的整数，验证失败返回 3
    """
    if padding is None:
        return 3
    
    try:
        num = int(padding)
        if num < 1:
            print(f"警告：补零位数不能小于1，使用默认值 3", file=__import__('sys').stderr)
            return 3
        if num > 10:
            print(f"警告：补零位数过大，使用最大值 10", file=__import__('sys').stderr)
            return 10
        return num
    except (ValueError, TypeError):
        print(f"警告：补零位数无效，使用默认值 3", file=__import__('sys').stderr)
        return 3


def validate_filename(filename: str) -> bool:
    """
    验证文件名是否合法（不包含非法字符）
    
    Args:
        filename: 文件名
        
    Returns:
        验证是否通过
    """
    if not filename:
        return False
    
    # Windows 非法字符: < > : " / \ | ? *
    # Unix/Linux 非法字符: /
    illegal_chars = '<>:"/\\|?*'
    
    for char in illegal_chars:
        if char in filename:
            print(f"错误：文件名包含非法字符 '{char}': {filename}", file=__import__('sys').stderr)
            return False
    
    # 检查是否以空格或点开头/结尾（Windows 问题）
    if filename.startswith(' ') or filename.endswith(' '):
        print(f"警告：文件名以空格开头或结尾: {filename}", file=__import__('sys').stderr)
    
    if filename.endswith('.'):
        print(f"警告：文件名以点结尾: {filename}", file=__import__('sys').stderr)
    
    return True


def is_protected_file(filename: str) -> bool:
    """
    检查文件是否受保护（禁止操作）
    
    Args:
        filename: 文件名
        
    Returns:
        是否受保护
    """
    if filename == PROTECTED_FILE:
        print(ERROR_MESSAGES['protected_file_access'].format(filename), file=__import__('sys').stderr)
        return True
    return False


def validate_all_inputs(
    ext: Optional[str] = None,
    date_format: Optional[str] = None,
    replace: Optional[str] = None,
    regex: Optional[str] = None,
    number_start: Optional[Union[int, str]] = None,
    padding: Optional[Union[int, str]] = None
) -> bool:
    """
    批量验证所有输入参数
    
    Args:
        ext: 扩展名字符串
        date_format: 日期格式字符串
        replace: 替换字符串
        regex: 正则替换字符串
        number_start: 序号起始值
        padding: 补零位数
        
    Returns:
        所有验证是否通过
    """
    all_valid = True
    
    # 验证扩展名
    if ext is not None:
        if validate_extensions(ext) is False:
            all_valid = False
    
    # 验证日期格式
    if date_format is not None:
        if not validate_date_format(date_format):
            all_valid = False
    
    # 验证替换字符串格式
    if replace is not None:
        if parse_replace_string(replace) is False:
            all_valid = False
    
    # 验证正则替换字符串格式
    if regex is not None:
        if parse_regex_replace(regex) is False:
            all_valid = False
    
    return all_valid
