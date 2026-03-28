"""
批量文件重命名工具 - FastAPI 测试服务

本模块提供自动化测试接口，用于测试所有核心功能：
- 重命名规则模块 (core_renamer.py)
- 重命名引擎 (rename_engine.py)
- 验证器 (utils/validators.py)
- 辅助函数 (utils/helpers.py)

测试接口列表：
- POST /test/rule       - 测试各种重命名规则
- POST /test/engine     - 测试完整重命名流程（预览模式）
- POST /test/conflicts  - 测试命名冲突检测
- POST /test/validators - 测试各种验证函数
- POST /test/e2e        - 端到端完整流程测试

强约束：
- 源文件目录（只读）：./source_data/
- 输出目录（只写）：./output_build/
- 严禁修改 .do_not_touch.cfg
"""

import os
import sys
import json
import tempfile
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core_renamer import (
    RenameRule,
    generate_new_filename,
    generate_rename_mapping,
    preview_rename,
    apply_prefix,
    apply_suffix,
    apply_replace,
    apply_number,
    apply_date,
    apply_regex
)
from rename_engine import RenameEngine
from utils.validators import (
    validate_source_dir,
    validate_output_dir,
    validate_extensions,
    validate_date_format,
    validate_regex,
    parse_replace_string,
    parse_regex_replace,
    validate_number_start,
    validate_padding,
    validate_filename,
    is_protected_file,
    validate_all_inputs
)
from utils.helpers import (
    split_filename,
    format_date_for_filename,
    safe_filename,
    format_preview_table,
    ensure_dir,
    list_files,
    get_file_modification_time
)
from utils.config import SOURCE_DIR, OUTPUT_DIR, PROTECTED_FILE

app = FastAPI(
    title="文件重命名工具测试 API",
    description="批量文件重命名工具的自动化测试接口",
    version="1.0.0"
)


# =============================================================================
# Pydantic 模型定义
# =============================================================================

class RuleTestRequest(BaseModel):
    """规则测试请求模型"""
    prefix: str = ""
    suffix: str = ""
    replace: Optional[str] = None
    number_start: int = 1
    padding: int = 3
    date_format: Optional[str] = None
    regex: Optional[str] = None
    test_files: List[str] = Field(default_factory=list, description="测试文件名列表")
    source_dir: str = Field(default=SOURCE_DIR, description="源文件目录（用于日期规则）")


class RuleTestResponse(BaseModel):
    """规则测试响应模型"""
    success: bool
    message: str
    rule_applied: Dict[str, Any]
    results: List[Dict[str, Any]]
    total_files: int


class EngineTestRequest(BaseModel):
    """引擎测试请求模型"""
    prefix: str = ""
    suffix: str = ""
    replace: Optional[str] = None
    number_start: int = 1
    padding: int = 3
    date_format: Optional[str] = None
    regex: Optional[str] = None
    extensions: Optional[str] = None
    source_dir: str = Field(default=SOURCE_DIR)


class EngineTestResponse(BaseModel):
    """引擎测试响应模型"""
    success: bool
    message: str
    source_dir: str
    files_found: int
    rename_mapping: Dict[str, str]
    conflicts: Dict[str, List[str]]
    stats: Dict[str, int]


class ConflictTestRequest(BaseModel):
    """冲突检测测试请求模型"""
    rename_mapping: Dict[str, str] = Field(description="模拟的重命名映射 {原文件名: 新文件名}")
    source_dir: str = Field(default=SOURCE_DIR)


class ConflictTestResponse(BaseModel):
    """冲突检测测试响应模型"""
    success: bool
    message: str
    has_conflicts: bool
    conflicts: Dict[str, List[str]]
    conflict_count: int


class ValidatorTestRequest(BaseModel):
    """验证器测试请求模型"""
    test_type: str = Field(description="测试类型: source_dir, output_dir, extensions, date_format, regex, replace, number_start, padding, filename, protected_file, all")
    test_value: Any = Field(description="待测试的值")
    extra_params: Optional[Dict[str, Any]] = Field(default=None, description="额外参数")


class ValidatorTestResponse(BaseModel):
    """验证器测试响应模型"""
    success: bool
    test_type: str
    input_value: Any
    result: Any
    is_valid: bool
    message: str


class E2ETestScenario(BaseModel):
    """端到端测试场景配置"""
    name: str = Field(description="场景名称")
    description: str = Field(description="场景描述")
    create_files: List[str] = Field(default_factory=list, description="要创建的测试文件")
    rule: Dict[str, Any] = Field(description="重命名规则配置")
    expected_results: Optional[Dict[str, str]] = Field(default=None, description="预期结果")


class E2ETestRequest(BaseModel):
    """端到端测试请求模型"""
    scenarios: List[E2ETestScenario] = Field(default_factory=list, description="测试场景列表")
    auto_cleanup: bool = Field(default=True, description="测试后是否自动清理")


class E2ETestResult(BaseModel):
    """单个场景测试结果"""
    scenario_name: str
    success: bool
    message: str
    files_created: List[str]
    rename_mapping: Dict[str, str]
    actual_results: Dict[str, Any]
    errors: List[str]


class E2ETestResponse(BaseModel):
    """端到端测试响应模型"""
    success: bool
    message: str
    temp_dir: str
    total_scenarios: int
    passed: int
    failed: int
    results: List[E2ETestResult]
    report_file: Optional[str] = None


class TestReportRequest(BaseModel):
    """测试报告生成请求"""
    include_timestamp: bool = Field(default=True)
    output_filename: str = Field(default="test_report.json")


# =============================================================================
# 辅助函数
# =============================================================================

def create_test_files(directory: str, filenames: List[str]) -> Tuple[List[str], List[str]]:
    """
    在指定目录创建测试文件
    
    Returns:
        (成功创建的文件列表, 错误列表)
    """
    created = []
    errors = []
    
    ensure_dir(directory)
    
    for filename in filenames:
        filepath = os.path.join(directory, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Test file created at {datetime.now().isoformat()}\n")
            created.append(filename)
        except Exception as e:
            errors.append(f"{filename}: {str(e)}")
    
    return created, errors


def cleanup_test_directory(directory: str) -> bool:
    """清理测试目录"""
    try:
        if os.path.exists(directory):
            shutil.rmtree(directory)
        return True
    except Exception:
        return False


def generate_test_report(results: List[Dict[str, Any]], output_path: str) -> bool:
    """生成 JSON 测试报告"""
    try:
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(results),
            'passed': sum(1 for r in results if r.get('success', False)),
            'failed': sum(1 for r in results if not r.get('success', False)),
            'results': results
        }
        
        ensure_dir(os.path.dirname(output_path))
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception:
        return False


# =============================================================================
# API 端点 - 规则测试
# =============================================================================

@app.post("/test/rule", response_model=RuleTestResponse)
async def test_rule(request: RuleTestRequest):
    """
    测试各种重命名规则
    
    输入：规则参数 + 测试文件名列表
    输出：重命名映射结果
    """
    try:
        # 创建规则对象
        rule = RenameRule(
            prefix=request.prefix,
            suffix=request.suffix,
            replace=request.replace,
            number_start=request.number_start,
            padding=request.padding,
            date_format=request.date_format,
            regex=request.regex
        )
        
        # 如果没有提供测试文件，使用默认测试文件
        test_files = request.test_files if request.test_files else [
            "photo.jpg",
            "document.txt",
            "image_001.png",
            "report.pdf",
            "data.csv"
        ]
        
        # 确保源目录存在（用于日期规则）
        source_dir = request.source_dir
        if not os.path.exists(source_dir):
            source_dir = SOURCE_DIR
        
        # 生成重命名映射
        results = []
        mapping = generate_rename_mapping(test_files, rule, source_dir)
        
        for old_name, new_name in mapping.items():
            results.append({
                "original": old_name,
                "new": new_name,
                "changed": old_name != new_name
            })
        
        return RuleTestResponse(
            success=True,
            message="规则测试完成",
            rule_applied={
                "prefix": request.prefix,
                "suffix": request.suffix,
                "replace": request.replace,
                "number_start": request.number_start,
                "padding": request.padding,
                "date_format": request.date_format,
                "regex": request.regex
            },
            results=results,
            total_files=len(test_files)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"规则测试失败: {str(e)}")


# =============================================================================
# API 端点 - 引擎测试
# =============================================================================

@app.post("/test/engine", response_model=EngineTestResponse)
async def test_engine(request: EngineTestRequest):
    """
    测试完整重命名流程（预览模式，不实际执行）
    
    输入：source_data/ 中的实际文件 + 规则
    输出：预览结果
    """
    try:
        source_dir = request.source_dir if os.path.exists(request.source_dir) else SOURCE_DIR
        
        # 创建引擎
        engine = RenameEngine(source_dir=source_dir)
        
        # 解析扩展名
        extensions = validate_extensions(request.extensions)
        
        # 获取文件列表
        files = engine.get_files(extensions)
        
        # 创建规则
        rule = RenameRule(
            prefix=request.prefix,
            suffix=request.suffix,
            replace=request.replace,
            number_start=request.number_start,
            padding=request.padding,
            date_format=request.date_format,
            regex=request.regex
        )
        
        # 生成重命名映射
        rename_mapping = engine.generate_rename_map(files, rule)
        
        # 检查冲突
        conflicts = engine.check_conflicts(rename_mapping)
        
        # 统计
        stats = {
            "total_files": len(files),
            "will_rename": sum(1 for old, new in rename_mapping.items() if old != new),
            "unchanged": sum(1 for old, new in rename_mapping.items() if old == new),
            "conflicts": len(conflicts)
        }
        
        return EngineTestResponse(
            success=True,
            message="引擎测试完成（预览模式）",
            source_dir=source_dir,
            files_found=len(files),
            rename_mapping=rename_mapping,
            conflicts=conflicts,
            stats=stats
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"引擎测试失败: {str(e)}")


# =============================================================================
# API 端点 - 冲突检测测试
# =============================================================================

@app.post("/test/conflicts", response_model=ConflictTestResponse)
async def test_conflicts(request: ConflictTestRequest):
    """
    测试命名冲突检测
    
    输入：模拟的重命名映射
    输出：冲突报告
    """
    try:
        source_dir = request.source_dir if os.path.exists(request.source_dir) else SOURCE_DIR
        engine = RenameEngine(source_dir=source_dir)
        
        # 检查冲突
        conflicts = engine.check_conflicts(request.rename_mapping)
        
        has_conflicts = len(conflicts) > 0
        
        return ConflictTestResponse(
            success=True,
            message="冲突检测完成" + (" - 发现冲突!" if has_conflicts else " - 无冲突"),
            has_conflicts=has_conflicts,
            conflicts=conflicts,
            conflict_count=len(conflicts)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"冲突检测失败: {str(e)}")


# =============================================================================
# API 端点 - 验证器测试
# =============================================================================

@app.post("/test/validators", response_model=ValidatorTestResponse)
async def test_validators(request: ValidatorTestRequest):
    """
    测试各种验证函数
    
    输入：待验证的数据
    输出：验证结果
    
    支持的 test_type:
    - source_dir: 验证源目录
    - output_dir: 验证输出目录
    - extensions: 验证扩展名
    - date_format: 验证日期格式
    - regex: 验证正则表达式
    - replace: 验证替换字符串格式
    - number_start: 验证序号起始值
    - padding: 验证补零位数
    - filename: 验证文件名
    - protected_file: 检查是否受保护文件
    - all: 批量验证所有参数
    """
    try:
        test_type = request.test_type.lower()
        test_value = request.test_value
        result = None
        is_valid = False
        message = ""
        
        if test_type == "source_dir":
            is_valid = validate_source_dir(str(test_value))
            result = is_valid
            message = "目录有效" if is_valid else "目录无效或不可读"
        
        elif test_type == "output_dir":
            is_valid = validate_output_dir(str(test_value))
            result = is_valid
            message = "目录有效" if is_valid else "目录无效或不可写"
        
        elif test_type == "extensions":
            result = validate_extensions(str(test_value))
            is_valid = result is not None
            message = f"扩展名列表: {result}" if is_valid else "扩展名格式无效"
        
        elif test_type == "date_format":
            is_valid = validate_date_format(str(test_value))
            result = is_valid
            message = "日期格式有效" if is_valid else "日期格式无效"
        
        elif test_type == "regex":
            is_valid = validate_regex(str(test_value))
            result = is_valid
            message = "正则表达式有效" if is_valid else "正则表达式无效"
        
        elif test_type == "replace":
            result = parse_replace_string(str(test_value))
            is_valid = result is not False and result is not None
            if result is None:
                message = "替换字符串为空"
            elif result is False:
                message = "替换字符串格式错误，应为 'old,new'"
            else:
                message = f"解析结果: old='{result[0]}', new='{result[1]}'"
        
        elif test_type == "regex_replace":
            result = parse_regex_replace(str(test_value))
            is_valid = result is not False and result is not None
            if result is None:
                message = "正则替换字符串为空"
            elif result is False:
                message = "正则替换字符串格式错误或正则无效"
            else:
                message = f"解析结果: pattern='{result[0]}', replacement='{result[1]}'"
        
        elif test_type == "number_start":
            result = validate_number_start(test_value)
            is_valid = True
            message = f"验证后的序号起始值: {result}"
        
        elif test_type == "padding":
            result = validate_padding(test_value)
            is_valid = True
            message = f"验证后的补零位数: {result}"
        
        elif test_type == "filename":
            is_valid = validate_filename(str(test_value))
            result = is_valid
            message = "文件名有效" if is_valid else "文件名包含非法字符"
        
        elif test_type == "protected_file":
            is_valid = is_protected_file(str(test_value))
            result = is_valid
            message = "是受保护文件" if is_valid else "不是受保护文件"
        
        elif test_type == "all":
            if isinstance(test_value, dict):
                is_valid = validate_all_inputs(**test_value)
                result = is_valid
                message = "所有验证通过" if is_valid else "部分验证失败"
            else:
                result = False
                message = "批量验证需要提供字典参数"
        
        else:
            raise HTTPException(status_code=400, detail=f"未知的测试类型: {test_type}")
        
        return ValidatorTestResponse(
            success=True,
            test_type=test_type,
            input_value=test_value,
            result=result,
            is_valid=is_valid if isinstance(is_valid, bool) else bool(result),
            message=message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证器测试失败: {str(e)}")


# =============================================================================
# API 端点 - 端到端测试
# =============================================================================

@app.post("/test/e2e", response_model=E2ETestResponse)
async def test_e2e(request: E2ETestRequest):
    """
    端到端完整流程测试
    
    流程：创建临时文件 -> 重命名 -> 验证 -> 清理
    输入：测试场景配置
    输出：测试结果报告
    """
    temp_dir = None
    results = []
    passed = 0
    failed = 0
    
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="rename_test_")
        
        # 如果没有提供场景，使用默认场景
        scenarios = request.scenarios if request.scenarios else get_default_scenarios()
        
        for scenario in scenarios:
            scenario_result = await run_e2e_scenario(temp_dir, scenario)
            results.append(scenario_result)
            
            if scenario_result.success:
                passed += 1
            else:
                failed += 1
        
        # 生成测试报告
        report_data = [r.dict() for r in results]
        report_file = os.path.join(OUTPUT_DIR, f"e2e_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        if generate_test_report(report_data, report_file):
            report_file_path = report_file
        else:
            report_file_path = None
        
        # 清理
        if request.auto_cleanup:
            cleanup_test_directory(temp_dir)
            temp_dir = "已清理"
        
        return E2ETestResponse(
            success=(failed == 0),
            message=f"端到端测试完成 - 通过: {passed}, 失败: {failed}",
            temp_dir=temp_dir if isinstance(temp_dir, str) else temp_dir,
            total_scenarios=len(scenarios),
            passed=passed,
            failed=failed,
            results=results,
            report_file=report_file_path
        )
    
    except Exception as e:
        # 清理临时目录
        if temp_dir and os.path.exists(temp_dir):
            cleanup_test_directory(temp_dir)
        
        raise HTTPException(status_code=500, detail=f"端到端测试失败: {str(e)}")


async def run_e2e_scenario(temp_dir: str, scenario: E2ETestScenario) -> E2ETestResult:
    """运行单个端到端测试场景"""
    errors = []
    files_created = []
    rename_mapping = {}
    actual_results = {}
    
    try:
        # 创建场景子目录
        scenario_dir = os.path.join(temp_dir, scenario.name.replace(" ", "_"))
        ensure_dir(scenario_dir)
        
        # 创建测试文件
        created, create_errors = create_test_files(scenario_dir, scenario.create_files)
        files_created = created
        errors.extend(create_errors)
        
        if not files_created:
            errors.append("没有成功创建任何测试文件")
            return E2ETestResult(
                scenario_name=scenario.name,
                success=False,
                message=f"场景 '{scenario.name}' 失败: 无法创建测试文件",
                files_created=files_created,
                rename_mapping=rename_mapping,
                actual_results=actual_results,
                errors=errors
            )
        
        # 创建引擎和规则
        engine = RenameEngine(source_dir=scenario_dir)
        rule = RenameRule(**scenario.rule)
        
        # 生成重命名映射
        rename_mapping = engine.generate_rename_map(files_created, rule)
        
        # 检查冲突
        conflicts = engine.check_conflicts(rename_mapping)
        if conflicts:
            errors.append(f"检测到命名冲突: {conflicts}")
        
        # 执行重命名
        results = engine.apply_rename(rename_mapping)
        
        # 验证结果
        for old_name, result in results.items():
            actual_results[old_name] = result
            if not result['success']:
                errors.append(f"重命名失败 {old_name}: {result.get('error', '未知错误')}")
        
        # 验证文件是否实际存在
        for old_name, new_name in rename_mapping.items():
            if old_name != new_name:
                old_path = os.path.join(scenario_dir, old_name)
                new_path = os.path.join(scenario_dir, new_name)
                
                if os.path.exists(old_path) and not os.path.exists(new_path):
                    errors.append(f"文件未成功重命名: {old_name}")
                elif not os.path.exists(new_path):
                    errors.append(f"新文件不存在: {new_name}")
        
        success = len(errors) == 0
        
        return E2ETestResult(
            scenario_name=scenario.name,
            success=success,
            message=f"场景 '{scenario.name}' {'通过' if success else '失败'}",
            files_created=files_created,
            rename_mapping=rename_mapping,
            actual_results=actual_results,
            errors=errors
        )
    
    except Exception as e:
        errors.append(f"场景执行异常: {str(e)}")
        return E2ETestResult(
            scenario_name=scenario.name,
            success=False,
            message=f"场景 '{scenario.name}' 执行异常",
            files_created=files_created,
            rename_mapping=rename_mapping,
            actual_results=actual_results,
            errors=errors
        )


def get_default_scenarios() -> List[E2ETestScenario]:
    """获取默认测试场景"""
    return [
        E2ETestScenario(
            name="基础前缀测试",
            description="测试添加前缀功能",
            create_files=["file1.txt", "file2.txt", "file3.txt"],
            rule={"prefix": "TEST_", "number_start": 1, "padding": 2},
            expected_results={}
        ),
        E2ETestScenario(
            name="字符串替换测试",
            description="测试字符串替换功能",
            create_files=["old_name_1.txt", "old_name_2.txt"],
            rule={"replace": "old_name,new_name"},
            expected_results={}
        ),
        E2ETestScenario(
            name="序号递增测试",
            description="测试序号递增功能",
            create_files=["doc.txt", "doc.txt", "doc.txt"],
            rule={"number_start": 1, "padding": 3},
            expected_results={}
        ),
        E2ETestScenario(
            name="组合规则测试",
            description="测试多种规则组合",
            create_files=["image.jpg", "photo.png", "pic.gif"],
            rule={
                "prefix": "IMG_",
                "suffix": "_2025",
                "number_start": 1,
                "padding": 3
            },
            expected_results={}
        ),
        E2ETestScenario(
            name="正则替换测试",
            description="测试正则表达式替换",
            create_files=["file_v1.txt", "file_v2.txt", "file_v3.txt"],
            rule={"regex": "_v(\\d+),_version$1"},
            expected_results={}
        )
    ]


# =============================================================================
# API 端点 - 健康检查
# =============================================================================

@app.get("/")
async def root():
    """API 根路径 - 服务信息"""
    return {
        "service": "文件重命名工具测试 API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": [
            {"path": "/test/rule", "method": "POST", "description": "测试重命名规则"},
            {"path": "/test/engine", "method": "POST", "description": "测试重命名引擎"},
            {"path": "/test/conflicts", "method": "POST", "description": "测试冲突检测"},
            {"path": "/test/validators", "method": "POST", "description": "测试验证器"},
            {"path": "/test/e2e", "method": "POST", "description": "端到端测试"}
        ]
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "source_dir_exists": os.path.exists(SOURCE_DIR),
        "output_dir_exists": os.path.exists(OUTPUT_DIR)
    }


# =============================================================================
# 主程序入口
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("文件重命名工具测试 API 服务")
    print("=" * 60)
    print(f"API 文档: http://localhost:8000/docs")
    print(f"健康检查: http://localhost:8000/health")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
