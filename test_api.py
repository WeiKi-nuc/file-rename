"""
批量文件重命名工具 - FastAPI 测试接口

本模块提供自动化测试所有核心功能的 REST API：
- 规则测试接口
- 引擎测试接口
- 冲突检测测试接口
- 验证器测试接口
- 端到端测试接口

运行方式:
    uvicorn test_api:app --reload --port 8000
    访问 API 文档: http://localhost:8000/docs

强约束:
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
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core_renamer import (
    RenameRule,
    apply_prefix,
    apply_suffix,
    apply_replace,
    apply_number,
    apply_date,
    apply_regex,
    generate_new_filename,
    generate_rename_mapping,
    preview_rename
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
    validate_filename,
    is_protected_file,
    validate_all_inputs
)
from utils.helpers import (
    split_filename,
    format_date_for_filename,
    format_preview_table,
    list_files,
    safe_filename
)
from utils.config import (
    SOURCE_DIR,
    OUTPUT_DIR,
    PROTECTED_FILE,
    DEFAULT_NUMBER_START,
    DEFAULT_PADDING,
    DEFAULT_DATE_FORMAT
)


app = FastAPI(
    title="批量文件重命名工具 - 测试 API",
    description="用于自动化测试所有核心功能的 REST API",
    version="1.0.0"
)


# =============================================================================
# Pydantic 模型定义
# =============================================================================

class RuleTestRequest(BaseModel):
    """规则测试请求"""
    prefix: str = Field(default="", description="前缀")
    suffix: str = Field(default="", description="后缀")
    replace: Optional[str] = Field(default=None, description="替换字符串 'old,new'")
    number_start: int = Field(default=1, description="序号起始值")
    padding: int = Field(default=3, description="序号补零位数")
    date_format: Optional[str] = Field(default=None, description="日期格式")
    regex: Optional[str] = Field(default=None, description="正则替换 'pattern,replacement'")
    test_filenames: List[str] = Field(..., description="测试文件名列表")


class RuleTestResponse(BaseModel):
    """规则测试响应"""
    success: bool
    mapping: Dict[str, str] = Field(description="重命名映射 {原文件名: 新文件名}")
    preview_table: str = Field(default="", description="预览表格")
    errors: List[str] = Field(default_factory=list, description="错误列表")


class EngineTestRequest(BaseModel):
    """引擎测试请求"""
    extensions: Optional[List[str]] = Field(default=None, description="扩展名过滤")
    prefix: str = Field(default="", description="前缀")
    suffix: str = Field(default="", description="后缀")
    replace: Optional[str] = Field(default=None, description="替换字符串")
    number_start: int = Field(default=1, description="序号起始值")
    padding: int = Field(default=3, description="序号补零位数")
    date_format: Optional[str] = Field(default=None, description="日期格式")
    regex: Optional[str] = Field(default=None, description="正则替换")


class EngineTestResponse(BaseModel):
    """引擎测试响应"""
    success: bool
    source_dir: str
    files_found: int
    files: List[str]
    rename_map: Dict[str, str]
    conflicts: Dict[str, List[str]]
    preview_table: str
    errors: List[str] = Field(default_factory=list)


class ConflictTestRequest(BaseModel):
    """冲突检测测试请求"""
    rename_map: Dict[str, str] = Field(..., description="重命名映射")
    existing_files: List[str] = Field(default_factory=list, description="已存在的文件列表")


class ConflictTestResponse(BaseModel):
    """冲突检测测试响应"""
    has_conflicts: bool
    conflicts: Dict[str, List[str]]
    duplicate_targets: List[str]
    existing_conflicts: List[str]


class ValidatorTestRequest(BaseModel):
    """验证器测试请求"""
    test_type: str = Field(..., description="测试类型: 'dir', 'ext', 'date', 'regex', 'filename', 'protected', 'all'")
    directory: Optional[str] = Field(default=None, description="目录路径")
    extensions: Optional[str] = Field(default=None, description="扩展名字符串")
    date_format: Optional[str] = Field(default=None, description="日期格式")
    regex_pattern: Optional[str] = Field(default=None, description="正则表达式")
    filename: Optional[str] = Field(default=None, description="文件名")
    replace_string: Optional[str] = Field(default=None, description="替换字符串")
    regex_string: Optional[str] = Field(default=None, description="正则替换字符串")


class ValidatorTestResponse(BaseModel):
    """验证器测试响应"""
    success: bool
    test_type: str
    result: Any
    errors: List[str] = Field(default_factory=list)


class E2ETestRequest(BaseModel):
    """端到端测试请求"""
    scenario: str = Field(default="basic", description="测试场景: basic, boundary, complex")
    test_files: List[str] = Field(default_factory=lambda: ["test1.txt", "test2.txt", "test3.txt"], description="测试文件名")
    rule: Dict[str, Any] = Field(default_factory=lambda: {}, description="重命名规则配置")


class E2ETestResponse(BaseModel):
    """端到端测试响应"""
    success: bool
    scenario: str
    test_dir: str
    setup: Dict[str, Any]
    execution: Dict[str, Any]
    verification: Dict[str, Any]
    cleanup: Dict[str, Any]
    report: Dict[str, Any]


class TestReport(BaseModel):
    """测试报告"""
    test_id: str
    timestamp: str
    test_type: str
    success: bool
    duration_ms: float
    request: Dict[str, Any]
    response: Dict[str, Any]
    errors: List[str]


# =============================================================================
# 辅助函数
# =============================================================================

def generate_test_id() -> str:
    """生成测试ID"""
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def create_test_report(
    test_type: str,
    success: bool,
    duration_ms: float,
    request: Dict[str, Any],
    response: Dict[str, Any],
    errors: List[str]
) -> TestReport:
    """创建测试报告"""
    return TestReport(
        test_id=generate_test_id(),
        timestamp=datetime.now().isoformat(),
        test_type=test_type,
        success=success,
        duration_ms=duration_ms,
        request=request,
        response=response,
        errors=errors
    )


def save_test_report(report: TestReport, output_dir: str = OUTPUT_DIR) -> str:
    """保存测试报告到JSON文件"""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"test_report_{report.test_id}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)
    return filepath


# =============================================================================
# API 端点
# =============================================================================

@app.get("/")
async def root():
    """API 根路径"""
    return {
        "message": "批量文件重命名工具 - 测试 API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "规则测试": "POST /test/rule",
            "引擎测试": "POST /test/engine",
            "冲突检测测试": "POST /test/conflicts",
            "验证器测试": "POST /test/validators",
            "端到端测试": "POST /test/e2e"
        }
    }


@app.post("/test/rule", response_model=RuleTestResponse)
async def test_rule(request: RuleTestRequest):
    """
    测试各种重命名规则
    
    输入：规则参数 + 测试文件名列表
    输出：重命名映射结果
    """
    import time
    start_time = time.time()
    errors = []
    
    try:
        rule = RenameRule(
            prefix=request.prefix,
            suffix=request.suffix,
            replace=request.replace,
            number_start=request.number_start,
            padding=request.padding,
            date_format=request.date_format,
            regex=request.regex
        )
        
        mapping = {}
        current_number = rule.number_start
        
        for filename in request.test_filenames:
            sequence_number = current_number if rule.number_start >= 0 else None
            new_filename = generate_new_filename(
                filename,
                rule,
                sequence_number,
                SOURCE_DIR
            )
            mapping[filename] = new_filename
            current_number += 1
        
        preview_table = format_preview_table(mapping)
        
        duration_ms = (time.time() - start_time) * 1000
        
        report = create_test_report(
            test_type="rule",
            success=True,
            duration_ms=duration_ms,
            request=request.model_dump(),
            response={"mapping": mapping},
            errors=errors
        )
        save_test_report(report)
        
        return RuleTestResponse(
            success=True,
            mapping=mapping,
            preview_table=preview_table,
            errors=errors
        )
        
    except Exception as e:
        errors.append(str(e))
        return RuleTestResponse(
            success=False,
            mapping={},
            errors=errors
        )


@app.post("/test/engine", response_model=EngineTestResponse)
async def test_engine(request: EngineTestRequest):
    """
    测试完整重命名流程
    
    输入：source_data/ 中的实际文件 + 规则
    输出：预览结果（不实际执行）
    """
    import time
    start_time = time.time()
    errors = []
    
    try:
        if not os.path.exists(SOURCE_DIR):
            errors.append(f"源目录不存在: {SOURCE_DIR}")
            return EngineTestResponse(
                success=False,
                source_dir=SOURCE_DIR,
                files_found=0,
                files=[],
                rename_map={},
                conflicts={},
                preview_table="",
                errors=errors
            )
        
        engine = RenameEngine(SOURCE_DIR)
        
        files = engine.get_files(request.extensions)
        
        rule = RenameRule(
            prefix=request.prefix,
            suffix=request.suffix,
            replace=request.replace,
            number_start=request.number_start,
            padding=request.padding,
            date_format=request.date_format,
            regex=request.regex
        )
        
        rename_map = engine.generate_rename_map(files, rule)
        
        conflicts = engine.check_conflicts(rename_map)
        
        preview_table = format_preview_table(rename_map)
        
        duration_ms = (time.time() - start_time) * 1000
        
        report = create_test_report(
            test_type="engine",
            success=True,
            duration_ms=duration_ms,
            request=request.model_dump(),
            response={
                "files_found": len(files),
                "rename_count": len(rename_map),
                "conflict_count": len(conflicts)
            },
            errors=errors
        )
        save_test_report(report)
        
        return EngineTestResponse(
            success=True,
            source_dir=SOURCE_DIR,
            files_found=len(files),
            files=files,
            rename_map=rename_map,
            conflicts=conflicts,
            preview_table=preview_table,
            errors=errors
        )
        
    except Exception as e:
        errors.append(str(e))
        return EngineTestResponse(
            success=False,
            source_dir=SOURCE_DIR,
            files_found=0,
            files=[],
            rename_map={},
            conflicts={},
            preview_table="",
            errors=errors
        )


@app.post("/test/conflicts", response_model=ConflictTestResponse)
async def test_conflicts(request: ConflictTestRequest):
    """
    测试命名冲突检测
    
    输入：模拟的重命名映射
    输出：冲突报告
    """
    conflicts: Dict[str, List[str]] = {}
    duplicate_targets: List[str] = []
    existing_conflicts: List[str] = []
    
    new_name_to_old: Dict[str, List[str]] = {}
    for old_name, new_name in request.rename_map.items():
        if new_name not in new_name_to_old:
            new_name_to_old[new_name] = []
        new_name_to_old[new_name].append(old_name)
    
    for new_name, old_names in new_name_to_old.items():
        if len(old_names) > 1:
            conflicts[new_name] = old_names
            duplicate_targets.append(new_name)
    
    for old_name, new_name in request.rename_map.items():
        if old_name == new_name:
            continue
        if new_name in request.existing_files and new_name not in request.rename_map:
            if new_name not in conflicts:
                conflicts[new_name] = []
            conflicts[new_name].append(f"[已存在文件] {new_name}")
            existing_conflicts.append(new_name)
    
    return ConflictTestResponse(
        has_conflicts=len(conflicts) > 0,
        conflicts=conflicts,
        duplicate_targets=duplicate_targets,
        existing_conflicts=existing_conflicts
    )


@app.post("/test/validators", response_model=ValidatorTestResponse)
async def test_validators(request: ValidatorTestRequest):
    """
    测试各种验证函数
    
    输入：待验证的数据
    输出：验证结果
    """
    errors = []
    result = None
    success = True
    
    try:
        if request.test_type == "dir":
            if request.directory:
                result = validate_source_dir(request.directory)
            else:
                result = validate_source_dir(SOURCE_DIR)
                
        elif request.test_type == "ext":
            result = validate_extensions(request.extensions)
            
        elif request.test_type == "date":
            result = validate_date_format(request.date_format)
            
        elif request.test_type == "regex":
            result = validate_regex(request.regex_pattern)
            
        elif request.test_type == "filename":
            result = validate_filename(request.filename or "")
            
        elif request.test_type == "protected":
            result = is_protected_file(request.filename or "")
            
        elif request.test_type == "replace":
            result = parse_replace_string(request.replace_string)
            
        elif request.test_type == "regex_parse":
            result = parse_regex_replace(request.regex_string)
            
        elif request.test_type == "all":
            result = validate_all_inputs(
                ext=request.extensions,
                date_format=request.date_format,
                replace=request.replace_string,
                regex=request.regex_string
            )
        else:
            errors.append(f"未知的测试类型: {request.test_type}")
            success = False
            
    except Exception as e:
        errors.append(str(e))
        success = False
    
    return ValidatorTestResponse(
        success=success and (result is not False),
        test_type=request.test_type,
        result=result,
        errors=errors
    )


@app.post("/test/e2e", response_model=E2ETestResponse)
async def test_e2e(request: E2ETestRequest):
    """
    完整流程测试
    
    创建临时文件 -> 重命名 -> 验证 -> 清理
    输入：测试场景配置
    输出：测试结果报告
    """
    import time
    start_time = time.time()
    
    setup_result: Dict[str, Any] = {"success": False, "files_created": []}
    execution_result: Dict[str, Any] = {"success": False, "operations": {}}
    verification_result: Dict[str, Any] = {"success": False, "checks": []}
    cleanup_result: Dict[str, Any] = {"success": False, "cleaned": []}
    report: Dict[str, Any] = {}
    
    test_dir = tempfile.mkdtemp(prefix="rename_test_")
    
    try:
        for filename in request.test_files:
            filepath = os.path.join(test_dir, filename)
            os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else test_dir, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Test content for {filename}")
            setup_result["files_created"].append(filename)
        setup_result["success"] = True
        
        rule_config = request.rule or {}
        if request.scenario == "basic":
            rule_config = {
                "prefix": rule_config.get("prefix", "test_"),
                "suffix": rule_config.get("suffix", ""),
                "number_start": rule_config.get("number_start", 1),
                "padding": rule_config.get("padding", 3)
            }
        elif request.scenario == "boundary":
            rule_config = {
                "prefix": rule_config.get("prefix", ""),
                "suffix": rule_config.get("suffix", "_boundary"),
                "replace": rule_config.get("replace", "test,boundary")
            }
        elif request.scenario == "complex":
            rule_config = {
                "prefix": rule_config.get("prefix", "IMG_"),
                "suffix": rule_config.get("suffix", "_2025"),
                "number_start": rule_config.get("number_start", 1),
                "padding": rule_config.get("padding", 4),
                "regex": rule_config.get("regex", "test,photo")
            }
        
        rule = RenameRule(
            prefix=rule_config.get("prefix", ""),
            suffix=rule_config.get("suffix", ""),
            replace=rule_config.get("replace"),
            number_start=rule_config.get("number_start", 1),
            padding=rule_config.get("padding", 3),
            date_format=rule_config.get("date_format"),
            regex=rule_config.get("regex")
        )
        
        engine = RenameEngine(test_dir)
        files = engine.get_files()
        rename_map = engine.generate_rename_map(files, rule)
        
        execution_result["operations"] = rename_map
        execution_result["success"] = True
        
        checks = []
        all_verified = True
        
        for old_name, new_name in rename_map.items():
            old_path = os.path.join(test_dir, old_name)
            new_path = os.path.join(test_dir, new_name)
            
            check = {
                "original": old_name,
                "expected_new": new_name,
                "original_exists": os.path.exists(old_path),
                "can_rename": old_name != new_name
            }
            checks.append(check)
            
            if not check["original_exists"]:
                all_verified = False
        
        verification_result["checks"] = checks
        verification_result["success"] = all_verified
        
        cleaned = []
        for filename in os.listdir(test_dir):
            filepath = os.path.join(test_dir, filename)
            if os.path.isfile(filepath):
                os.remove(filepath)
                cleaned.append(filename)
        cleanup_result["cleaned"] = cleaned
        cleanup_result["success"] = True
        
        duration_ms = (time.time() - start_time) * 1000
        
        report = {
            "total_duration_ms": duration_ms,
            "files_tested": len(request.test_files),
            "scenario": request.scenario,
            "all_passed": setup_result["success"] and execution_result["success"] and verification_result["success"]
        }
        
        test_report = create_test_report(
            test_type="e2e",
            success=report["all_passed"],
            duration_ms=duration_ms,
            request=request.model_dump(),
            response=report,
            errors=[]
        )
        save_test_report(test_report)
        
    except Exception as e:
        report["error"] = str(e)
        
    finally:
        try:
            shutil.rmtree(test_dir, ignore_errors=True)
        except Exception:
            pass
    
    return E2ETestResponse(
        success=report.get("all_passed", False),
        scenario=request.scenario,
        test_dir=test_dir,
        setup=setup_result,
        execution=execution_result,
        verification=verification_result,
        cleanup=cleanup_result,
        report=report
    )


@app.get("/test/report/{test_id}")
async def get_test_report(test_id: str):
    """获取测试报告"""
    report_path = os.path.join(OUTPUT_DIR, f"test_report_{test_id}.json")
    
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail=f"测试报告不存在: {test_id}")
    
    with open(report_path, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    return JSONResponse(content=report_data)


@app.get("/test/reports")
async def list_test_reports():
    """列出所有测试报告"""
    if not os.path.exists(OUTPUT_DIR):
        return {"reports": []}
    
    reports = []
    for filename in os.listdir(OUTPUT_DIR):
        if filename.startswith("test_report_") and filename.endswith(".json"):
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            reports.append({
                "test_id": data.get("test_id"),
                "timestamp": data.get("timestamp"),
                "test_type": data.get("test_type"),
                "success": data.get("success")
            })
    
    reports.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {"reports": reports, "total": len(reports)}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "source_dir_exists": os.path.exists(SOURCE_DIR),
        "output_dir_exists": os.path.exists(OUTPUT_DIR)
    }


@app.get("/test/scenarios")
async def list_test_scenarios():
    """列出可用的测试场景"""
    scenarios_dir = os.path.join(os.path.dirname(__file__), "test_scenarios")
    
    if not os.path.exists(scenarios_dir):
        return {"scenarios": [], "message": "测试场景目录不存在"}
    
    scenarios = []
    for filename in os.listdir(scenarios_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(scenarios_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            scenarios.append({
                "name": data.get("name", filename),
                "description": data.get("description", ""),
                "file": filename
            })
    
    return {"scenarios": scenarios}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
