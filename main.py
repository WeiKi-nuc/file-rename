"""
批量文件重命名工具 - 主入口模块

本模块是程序的唯一入口，负责：
- 解析命令行参数
- 协调各子模块工作
- 控制程序主流程

强约束：
- 源文件目录（只读）：./source_data/
- 输出目录（只写）：./output_build/
- 严禁修改 .do_not_touch.cfg
"""

import sys
import os
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli_parser import create_parser, parse_args
from core_renamer import RenameRule, generate_new_filename
from rename_engine import RenameEngine
from utils.config import SOURCE_DIR, OUTPUT_DIR, PREVIEW_FILE, LOG_FILE
from utils.validators import validate_source_dir, validate_output_dir, validate_extensions
from utils.helpers import ensure_dir, format_preview_table, save_preview, save_log, load_log


def run_preview(args) -> int:
    """
    执行预览命令
    
    Args:
        args: 解析后的命令行参数
        
    Returns:
        退出码 (0=成功, 1=失败)
    """
    try:
        # 验证源目录
        if not validate_source_dir(SOURCE_DIR):
            return 1
        
        # 确保输出目录存在
        if not ensure_dir(OUTPUT_DIR):
            print(f"错误：无法创建输出目录 {OUTPUT_DIR}", file=sys.stderr)
            return 1
        
        # 验证扩展名
        extensions = validate_extensions(args.ext) if args.ext else None
        
        # 创建重命名引擎
        engine = RenameEngine(SOURCE_DIR)
        
        # 获取文件列表
        files = engine.get_files(extensions)
        if not files:
            print(f"未在 {SOURCE_DIR} 中找到匹配的文件")
            return 0
        
        # 创建重命名规则
        rule = RenameRule(
            prefix=args.prefix or "",
            suffix=args.suffix or "",
            replace=args.replace,
            number_start=args.number_start,
            padding=args.padding,
            date_format=args.date_format,
            regex=args.regex
        )
        
        # 生成重命名映射
        rename_map = engine.generate_rename_map(files, rule)
        
        if not rename_map:
            print("没有需要重命名的文件")
            return 0
        
        # 检查冲突
        conflicts = engine.check_conflicts(rename_map)
        if conflicts:
            print("警告：检测到以下命名冲突：")
            for new_name, old_names in conflicts.items():
                print(f"  '{new_name}' 将由以下文件生成：{old_names}")
        
        # 显示预览表格
        table = format_preview_table(rename_map)
        print(table)
        print(f"\n共 {len(rename_map)} 个文件")
        
        # 保存预览到文件
        preview_path = os.path.join(OUTPUT_DIR, PREVIEW_FILE)
        if save_preview(rename_map, preview_path):
            print(f"预览已保存到: {preview_path}")
        
        return 0
        
    except Exception as e:
        print(f"预览失败: {e}", file=sys.stderr)
        return 1


def run_apply(args) -> int:
    """
    执行应用命令（实际重命名）
    
    Args:
        args: 解析后的命令行参数
        
    Returns:
        退出码 (0=成功, 1=失败)
    """
    try:
        # 验证源目录
        if not validate_source_dir(SOURCE_DIR):
            return 1
        
        # 确保输出目录存在
        if not ensure_dir(OUTPUT_DIR):
            print(f"错误：无法创建输出目录 {OUTPUT_DIR}", file=sys.stderr)
            return 1
        
        # 验证扩展名
        extensions = validate_extensions(args.ext) if args.ext else None
        
        # 创建重命名引擎
        engine = RenameEngine(SOURCE_DIR)
        
        # 获取文件列表
        files = engine.get_files(extensions)
        if not files:
            print(f"未在 {SOURCE_DIR} 中找到匹配的文件")
            return 0
        
        # 创建重命名规则
        rule = RenameRule(
            prefix=args.prefix or "",
            suffix=args.suffix or "",
            replace=args.replace,
            number_start=args.number_start,
            padding=args.padding,
            date_format=args.date_format,
            regex=args.regex
        )
        
        # 生成重命名映射
        rename_map = engine.generate_rename_map(files, rule)
        
        if not rename_map:
            print("没有需要重命名的文件")
            return 0
        
        # 检查冲突
        conflicts = engine.check_conflicts(rename_map)
        if conflicts:
            print("错误：检测到命名冲突，无法执行重命名：")
            for new_name, old_names in conflicts.items():
                print(f"  '{new_name}' 将由以下文件生成：{old_names}")
            return 1
        
        # 显示预览并确认
        table = format_preview_table(rename_map)
        print(table)
        print(f"\n共 {len(rename_map)} 个文件将被重命名")
        
        # 如果没有 --yes 参数，询问确认
        if not args.yes:
            response = input("确认执行重命名? [y/N]: ").strip().lower()
            if response not in ('y', 'yes'):
                print("操作已取消")
                return 0
        
        # 执行重命名
        results = engine.apply_rename(rename_map)
        
        # 统计结果
        success_count = sum(1 for r in results.values() if r['success'])
        fail_count = len(results) - success_count
        
        print(f"\n重命名完成: 成功 {success_count} 个, 失败 {fail_count} 个")
        
        # 显示失败的项
        for old_name, result in results.items():
            if not result['success']:
                print(f"  失败: {old_name} -> {result.get('error', '未知错误')}")
        
        # 保存日志
        log_path = os.path.join(OUTPUT_DIR, LOG_FILE)
        if save_log(results, log_path):
            print(f"操作日志已保存到: {log_path}")
        
        return 0 if fail_count == 0 else 1
        
    except Exception as e:
        print(f"重命名失败: {e}", file=sys.stderr)
        return 1


def run_undo(args) -> int:
    """
    执行撤销命令
    
    Args:
        args: 解析后的命令行参数
        
    Returns:
        退出码 (0=成功, 1=失败)
    """
    try:
        # 验证源目录
        if not validate_source_dir(SOURCE_DIR):
            return 1
        
        # 加载日志文件
        log_path = os.path.join(OUTPUT_DIR, LOG_FILE)
        if not os.path.exists(log_path):
            print(f"错误：找不到日志文件 {log_path}", file=sys.stderr)
            return 1
        
        log_data = load_log(log_path)
        if not log_data:
            print("错误：日志文件为空或格式不正确", file=sys.stderr)
            return 1
        
        # 创建重命名引擎
        engine = RenameEngine(SOURCE_DIR)
        
        # 构建撤销映射（新名 -> 旧名）
        undo_map = {}
        for old_name, info in log_data.items():
            if isinstance(info, dict) and info.get('success') and info.get('new_name'):
                new_name = info['new_name']
                # 检查当前文件是否存在
                new_path = os.path.join(SOURCE_DIR, new_name)
                if os.path.exists(new_path):
                    undo_map[new_name] = old_name
        
        if not undo_map:
            print("没有可以撤销的操作")
            return 0
        
        # 显示撤销预览
        print("将要撤销以下重命名操作：")
        for new_name, old_name in undo_map.items():
            print(f"  {new_name} -> {old_name}")
        print(f"\n共 {len(undo_map)} 个文件")
        
        # 确认
        if not args.yes:
            response = input("确认撤销? [y/N]: ").strip().lower()
            if response not in ('y', 'yes'):
                print("操作已取消")
                return 0
        
        # 执行撤销（undo_map 已经是 新名->旧名，直接传入）
        results = engine.apply_rename(undo_map, undo_mode=True)
        
        # 统计结果
        success_count = sum(1 for r in results.values() if r['success'])
        fail_count = len(results) - success_count
        
        print(f"\n撤销完成: 成功 {success_count} 个, 失败 {fail_count} 个")
        
        return 0 if fail_count == 0 else 1
        
    except Exception as e:
        print(f"撤销失败: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """
    程序主入口
    
    Returns:
        退出码
    """
    parser = create_parser()
    args = parse_args(parser)
    
    if args.command == 'preview':
        return run_preview(args)
    elif args.command == 'apply':
        return run_apply(args)
    elif args.command == 'undo':
        return run_undo(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
