"""
批量文件重命名工具 - 配置常量模块

本模块定义程序中使用的所有常量：
- 目录路径
- 文件名
- 支持的日期格式
- 其他配置项

强约束：
- 源文件目录（只读）：./source_data/
- 输出目录（只写）：./output_build/
- 严禁修改 .do_not_touch.cfg
"""

import os
from typing import List, Tuple

# =============================================================================
# 目录路径配置
# =============================================================================

# 源文件目录（只读）- 用户文件存放处
SOURCE_DIR: str = './source_data/'

# 输出目录（只写）- 用于保存预览文本、日志JSON等
OUTPUT_DIR: str = './output_build/'

# 受保护文件 - 绝对禁止修改、重命名、删除
PROTECTED_FILE: str = '.do_not_touch.cfg'


# =============================================================================
# 输出文件名配置
# =============================================================================

# 预览输出文件名
PREVIEW_FILE: str = 'rename_preview.txt'

# 操作日志文件名
LOG_FILE: str = 'rename_log.json'


# =============================================================================
# 重命名规则默认值
# =============================================================================

# 默认序号起始值
DEFAULT_NUMBER_START: int = 1

# 默认序号补零位数
DEFAULT_PADDING: int = 3

# 默认日期格式
DEFAULT_DATE_FORMAT: str = '%Y%m%d'


# =============================================================================
# 支持的日期格式列表
# =============================================================================

SUPPORTED_DATE_FORMATS: List[str] = [
    '%Y%m%d',           # 20250317
    '%Y-%m-%d',         # 2025-03-17
    '%Y_%m_%d',         # 2025_03_17
    '%Y%m%d_%H%M%S',    # 20250317_143052
    '%Y-%m-%d_%H-%M-%S', # 2025-03-17_14-30-52
    '%d%m%Y',           # 17032025
    '%d-%m-%Y',         # 17-03-2025
    '%m%d%Y',           # 03172025
    '%m-%d-%Y',         # 03-17-2025
]


# =============================================================================
# 文件扩展名配置
# =============================================================================

# 默认处理的扩展名（None 表示所有文件）
DEFAULT_EXTENSIONS: List[str] = []

# 受保护的扩展名（不允许处理，防止误操作系统文件）
PROTECTED_EXTENSIONS: List[str] = [
    '.cfg',   # 配置文件
    '.sys',   # 系统文件
    '.dll',   # 动态链接库
    '.exe',   # 可执行文件
]


# =============================================================================
# 表格输出配置
# =============================================================================

# 预览表格列宽
PREVIEW_TABLE_CONFIG: dict = {
    'index_width': 6,
    'old_name_width': 40,
    'new_name_width': 40,
    'status_width': 10,
}


# =============================================================================
# 错误消息配置
# =============================================================================

ERROR_MESSAGES: dict = {
    'source_dir_not_exist': '错误：源目录不存在: {}',
    'source_dir_not_readable': '错误：源目录不可读: {}',
    'output_dir_create_failed': '错误：无法创建输出目录: {}',
    'protected_file_access': '错误：禁止访问受保护文件: {}',
    'invalid_extension': '错误：无效的扩展名格式: {}',
    'invalid_date_format': '错误：无效的日期格式: {}',
    'invalid_regex': '错误：无效的正则表达式: {}',
    'file_not_found': '错误：文件不存在: {}',
    'permission_denied': '错误：权限不足: {}',
    'name_conflict': '错误：命名冲突: {}',
    'rename_failed': '错误：重命名失败: {}',
}


# =============================================================================
# 路径辅助函数
# =============================================================================

def get_source_path(filename: str = '') -> str:
    """
    获取源目录中的文件路径
    
    Args:
        filename: 文件名（可选）
        
    Returns:
        完整路径
    """
    if filename:
        return os.path.join(SOURCE_DIR, filename)
    return SOURCE_DIR


def get_output_path(filename: str = '') -> str:
    """
    获取输出目录中的文件路径
    
    Args:
        filename: 文件名（可选）
        
    Returns:
        完整路径
    """
    if filename:
        return os.path.join(OUTPUT_DIR, filename)
    return OUTPUT_DIR


def is_protected_file(filename: str) -> bool:
    """
    检查文件是否受保护
    
    Args:
        filename: 文件名
        
    Returns:
        是否受保护
    """
    return filename == PROTECTED_FILE


def normalize_path(path: str) -> str:
    """
    规范化路径（统一使用正斜杠）
    
    Args:
        path: 原始路径
        
    Returns:
        规范化后的路径
    """
    return path.replace('\\', '/')
