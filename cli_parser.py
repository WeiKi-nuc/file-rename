"""
批量文件重命名工具 - 命令行参数解析模块

本模块负责：
- 定义命令行参数和子命令
- 解析用户输入
- 提供参数验证

支持的子命令：
- preview: 预览重命名效果
- apply: 实际执行重命名
- undo: 撤销上一次重命名

强约束：
- 源文件目录（只读）：./source_data/
- 输出目录（只写）：./output_build/
- 严禁修改 .do_not_touch.cfg
"""

import argparse
import sys
from typing import Optional, Sequence

from utils.config import (
    DEFAULT_NUMBER_START, DEFAULT_PADDING, DEFAULT_DATE_FORMAT
)


def create_parser() -> argparse.ArgumentParser:
    """
    创建命令行参数解析器
    
    Returns:
        配置好的 ArgumentParser 实例
    """
    parser = argparse.ArgumentParser(
        prog='batch_rename',
        description='批量文件重命名工具 - 支持多种重命名规则',
        epilog='示例: python main.py preview --prefix "IMG_" --ext jpg,png',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 子命令
    subparsers = parser.add_subparsers(
        dest='command',
        help='可用命令',
        title='子命令'
    )
    
    # ==========================================================================
    # preview 子命令
    # ==========================================================================
    preview_parser = subparsers.add_parser(
        'preview',
        help='预览重命名效果（不实际执行）',
        description='预览重命名效果，输出新旧文件名对应表到 output_build/rename_preview.txt'
    )
    _add_common_args(preview_parser)
    
    # ==========================================================================
    # apply 子命令
    # ==========================================================================
    apply_parser = subparsers.add_parser(
        'apply',
        help='实际执行重命名',
        description='执行文件重命名操作，操作日志保存到 output_build/rename_log.json'
    )
    _add_common_args(apply_parser)
    apply_parser.add_argument(
        '--yes', '-y',
        action='store_true',
        dest='yes',
        help='跳过确认提示，直接执行（谨慎使用）'
    )
    
    # ==========================================================================
    # undo 子命令
    # ==========================================================================
    undo_parser = subparsers.add_parser(
        'undo',
        help='撤销上一次重命名操作',
        description='根据 output_build/rename_log.json 撤销上一次重命名操作'
    )
    undo_parser.add_argument(
        '--yes', '-y',
        action='store_true',
        dest='yes',
        help='跳过确认提示，直接执行（谨慎使用）'
    )
    
    return parser


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """
    添加通用参数（preview 和 apply 共用）
    
    Args:
        parser: 参数解析器
    """
    # 扩展名过滤
    parser.add_argument(
        '--ext',
        type=str,
        default=None,
        metavar='EXT',
        help='只处理指定扩展名的文件，多个用逗号分隔，如：jpg,png,txt（默认：所有文件）'
    )
    
    # 前缀
    parser.add_argument(
        '--prefix',
        type=str,
        default=None,
        metavar='PREFIX',
        help='添加前缀，如：--prefix "IMG_"'
    )
    
    # 后缀
    parser.add_argument(
        '--suffix',
        type=str,
        default=None,
        metavar='SUFFIX',
        help='添加后缀（在扩展名前），如：--suffix "_2025"'
    )
    
    # 字符串替换
    parser.add_argument(
        '--replace',
        type=str,
        default=None,
        metavar='OLD,NEW',
        help='字符串替换，格式：old,new，如：--replace "old,new"'
    )
    
    # 序号起始
    parser.add_argument(
        '--number-start',
        type=int,
        default=DEFAULT_NUMBER_START,
        metavar='N',
        help=f'序号起始值（默认：{DEFAULT_NUMBER_START}）'
    )
    
    # 序号补零位数
    parser.add_argument(
        '--padding',
        type=int,
        default=DEFAULT_PADDING,
        metavar='N',
        help=f'序号补零位数（默认：{DEFAULT_PADDING}，如 3 表示 001,002...）'
    )
    
    # 日期格式
    parser.add_argument(
        '--date-format',
        type=str,
        default=None,
        metavar='FORMAT',
        help='使用文件修改日期，指定格式（默认：Ymd），如：20250317'
    )
    
    # 正则替换
    parser.add_argument(
        '--regex',
        type=str,
        default=None,
        metavar='PATTERN,REPL',
        help='正则替换，格式：pattern,replacement，如：--regex "^IMG_(.*)$,Photo_\\1"'
    )


def parse_args(parser: argparse.ArgumentParser, args: Optional[Sequence[str]] = None):
    """
    解析命令行参数
    
    Args:
        parser: 参数解析器
        args: 参数列表（用于测试），None 表示使用 sys.argv
        
    Returns:
        解析后的参数命名空间
    """
    parsed = parser.parse_args(args)
    
    # 如果没有指定子命令，显示帮助
    if parsed.command is None:
        parser.print_help()
        sys.exit(1)
    
    return parsed


def validate_parsed_args(args) -> bool:
    """
    验证解析后的参数
    
    Args:
        args: 解析后的参数
        
    Returns:
        验证是否通过
    """
    from utils.validators import (
        validate_extensions, validate_date_format,
        parse_replace_string, parse_regex_replace,
        validate_number_start, validate_padding
    )
    
    # undo 命令不需要验证这些参数
    if args.command == 'undo':
        return True
    
    all_valid = True
    
    # 验证扩展名
    if args.ext is not None:
        if validate_extensions(args.ext) is False:
            all_valid = False
    
    # 验证日期格式
    if args.date_format is not None:
        if not validate_date_format(args.date_format):
            all_valid = False
    
    # 验证替换字符串
    if args.replace is not None:
        if parse_replace_string(args.replace) is False:
            all_valid = False
    
    # 验证正则替换
    if args.regex is not None:
        if parse_regex_replace(args.regex) is False:
            all_valid = False
    
    # 验证序号参数
    if hasattr(args, 'number_start'):
        args.number_start = validate_number_start(args.number_start)
    
    if hasattr(args, 'padding'):
        args.padding = validate_padding(args.padding)
    
    return all_valid


# 用于直接测试
if __name__ == '__main__':
    parser = create_parser()
    args = parse_args(parser)
    print(f"命令: {args.command}")
    print(f"参数: {args}")
