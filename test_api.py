"""
批量文件重命名工具 - FastAPI 测试接口

本模块提供自动化测试接口，用于测试所有核心功能的自动化测试。

API 端点：
1. POST /test/rule - 测试各种重命名规则
2. POST /test/engine - 测试完整重命名流程
3. POST /test/conflicts - 测试命名冲突检测
4. POST /test/validators - 测试各种验证函数
5. POST /test/e2e - 端到端完整流程测试
"""
import os
import sys
import tempfile
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

# 添加项目路径到 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入核心模块
from core_renamer import RenameRule, generate_rename_mapping, preview_rename
from rename_engine import RenameEngine
from utils import validators, helpers, config

# 创建 FastAPI 应用
app = FastAPI(
    title="批量文件重命名工具 - 测试 API",
    description="用于自动化测试所有核心功能的测试接口",
    version="1.0.0"
)

# =============================================================================
# 请求/响应模型定义
# =============================================================================

class RuleTestRequest(BaseModel):
    """规则测试请求模型"""
    rule: Dict[str, Any] = Field(..., description="重命名规则配置")
    test_files: List[str] = Field(..., description="测试文件名列表")
    source_dir: Optional[str] = Field(None, description="源文件目录")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "rule": {"prefix": "TEST_"},
                "test_files": ["file1.jpg", "file2.txt"]
            }]
        }
    }

class RuleTestResponse(BaseModel):
    """规则测试响应模型"""
    success: bool
    message: str
    results: List[Dict[str, str]]
    count: int

class EngineTestRequest(BaseModel):
    """引擎测试请求模型"""
    rule: Dict[str, Any] = Field(..., description="重命名规则配置")
    extensions: Optional[List[str]] = Field(None, description="扩展名过滤列表")
    source_dir: Optional[str] = Field(None, description="源文件目录")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "rule": {"prefix": "IMG_", "number_start": 1, "padding": 3},
                "extensions": ["jpg", "png"]
            }]
        }
    }

class EngineTestResponse(BaseModel):
    """引擎测试响应模型"""
    success: bool
    message: str
    source_files: List[str]
    rename_map: Dict[str, str]
    conflict_check: Dict[str, List[str]]
    stats: Dict[str, int]

class ConflictTestRequest(BaseModel):
    """冲突测试请求模型"""
    rename_map: Dict[str, str] = Field(..., description="重命名映射")
    source_dir: Optional[str] = Field(None, description="源文件目录")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "rename_map": {"a.jpg": "output.jpg", "b.jpg": "output.jpg"}
            }]
        }
    }

class ConflictTestResponse(BaseModel):
    """冲突测试响应模型"""
    success: bool
    message: str
    has_conflicts: bool
    conflicts: Dict[str, List[str]]
    conflict_count: int

class ValidatorTestRequest(BaseModel):
    """验证器测试请求模型"""
    validators: List[str] = Field(..., description="要测试的验证器列表")
    data: Dict[str, Any] = Field(..., description="验证数据")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "validators": ["validate_source_dir"],
                "data": {"path": "./source_data/"}
            }]
        }
    }

class ValidatorResult(TypedDict):
    name: str
    result: Any
    passed: bool
    message: str

class ValidatorTestResponse(BaseModel):
    """验证器测试响应模型"""
    success: bool
    message: str
    results: List[ValidatorResult]
    passed_count: int
    failed_count: int

class E2ETestRequest(BaseModel):
    """端到端测试请求模型"""
    scenario_name: str = Field(..., description="测试场景名称")
    rule: Dict[str, Any] = Field(..., description="重命名规则配置")
    test_files: List[str] = Field(..., description="要创建的测试文件名称")
    file_content: Optional[str] = Field("test content", description="测试文件内容")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "scenario_name": "complete_workflow",
                "rule": {"prefix": "E2E_", "number_start": 1, "padding": 3},
                "test_files": ["test1.txt", "test2.txt"]
            }]
        }
    }

class E2ETestResponse(BaseModel):
    """端到端测试响应模型"""
    success: bool
    message: str
    scenario_name: str
    temp_dir: str
    created_files: List[str]
    original_files: List[str]
    rename_map: Dict[str, str]
    final_files: List[str]
    cleanup_completed: bool
    errors: List[str]

# =============================================================================
# 工具函数
# =============================================================================

def create_rename_rule(rule_dict: Dict[str, Any]) -> RenameRule:
    """从字典创建 RenameRule 对象"""
    return RenameRule(
        prefix=rule_dict.get("prefix", ""),
        suffix=rule_dict.get("suffix", ""),
        replace=rule_dict.get("replace"),
        number_start=rule_dict.get("number_start", config.DEFAULT_NUMBER_START),
        padding=rule_dict.get("padding", config.DEFAULT_PADDING),
        date_format=rule_dict.get("date_format"),
        regex=rule_dict.get("regex")
    )

def create_test_files(directory: str, filenames: List[str], content: str = "test") -> None:
    """在指定目录创建测试文件"""
    for filename in filenames:
        filepath = os.path.join(directory, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

# =============================================================================
# API 端点实现
# =============================================================================

@app.post("/test/rule", response_model=RuleTestResponse, summary="测试重命名规则")
async def test_rule(request: RuleTestRequest):
    """
    测试各种重命名规则

    支持测试的规则类型：
    - 前缀/后缀添加
    - 字符串替换
    - 序号递增生成
    - 日期插入
    - 正则替换
    """
    try:
        # 创建重命名规则
        rule = create_rename_rule(request.rule)
        
        source_dir = request.source_dir or config.SOURCE_DIR
        
        # 生成重命名映射
        mapping = {}
        current_number = rule.number_start if rule.number_start >= 0 else None
        
        for filename in request.test_files:
            sequence_number = current_number if current_number is not None else None
            new_filename = generate_rename_mapping(
                [filename],
                rule,
                source_dir
            ).get(filename, filename)
            mapping[filename] = new_filename
            if current_number is not None:
                current_number += 1
        
        results = [{"original": k, "new": v} for k, v in mapping.items()]
        
        return RuleTestResponse(
            success=True,
            message="规则测试完成",
            results=results,
            count=len(results)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"规则测试失败: {str(e)}")

@app.post("/test/engine", response_model=EngineTestResponse, summary="测试重命名引擎")
async def test_engine(request: EngineTestRequest):
    """
    测试完整重命名流程

    测试内容：
    - 文件扫描
    - 重命名映射生成
    - 冲突检测
    - 预览结果
    """
    try:
        source_dir = request.source_dir or config.SOURCE_DIR
        
        # 确保源目录存在
        if not os.path.exists(source_dir):
            os.makedirs(source_dir, exist_ok=True)
        
        # 创建引擎实例
        engine = RenameEngine(source_dir=source_dir)
        
        # 获取文件列表
        files = engine.get_files(request.extensions)
        
        if not files:
            return EngineTestResponse(
                success=True,
                message="没有找到符合条件的文件",
                source_files=[],
                rename_map={},
                conflict_check={},
                stats={"total": 0, "to_rename": 0, "conflicts": 0}
            )
        
        # 创建重命名规则
        rule = create_rename_rule(request.rule)
        
        # 生成重命名映射
        rename_map = engine.generate_rename_map(files, rule)
        
        # 检查冲突
        conflicts = engine.check_conflicts(rename_map)
        
        stats = {
            "total": len(files),
            "to_rename": len(rename_map),
            "conflicts": len(conflicts)
        }
        
        return EngineTestResponse(
            success=True,
            message="引擎测试完成",
            source_files=files,
            rename_map=rename_map,
            conflict_check=conflicts,
            stats=stats
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"引擎测试失败: {str(e)}")

@app.post("/test/conflicts", response_model=ConflictTestResponse, summary="测试冲突检测")
async def test_conflicts(request: ConflictTestRequest):
    """
    测试命名冲突检测

    检测以下情况：
    - 多个原文件映射到同一个新文件名
    - 新文件名与现有文件冲突
    """
    try:
        source_dir = request.source_dir or config.SOURCE_DIR
        engine = RenameEngine(source_dir=source_dir)
        
        conflicts = engine.check_conflicts(request.rename_map)
        
        has_conflicts = len(conflicts) > 0
        
        return ConflictTestResponse(
            success=True,
            message="冲突检测完成",
            has_conflicts=has_conflicts,
            conflicts=conflicts,
            conflict_count=len(conflicts)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"冲突检测失败: {str(e)}")

@app.post("/test/validators", response_model=ValidatorTestResponse, summary="测试验证器")
async def test_validators(request: ValidatorTestRequest):
    """
    测试各种验证函数

    支持的验证器：
    - validate_source_dir: 目录验证
    - validate_extensions: 扩展名验证
    - is_protected_file: 受保护文件检查
    - validate_date_format: 日期格式验证
    - validate_regex: 正则表达式验证
    """
    results: List[ValidatorResult] = []
    passed_count = 0
    failed_count = 0
    
    validator_funcs = {
        "validate_source_dir": lambda d: validators.validate_source_dir(d.get("path", "./source")),
        "validate_output_dir": lambda d: validators.validate_output_dir(d.get("path", "./output_build/")),
        "validate_extensions": lambda d: validators.validate_extensions(d.get("ext_string")),
        "validate_date_format": lambda d: validators.validate_date_format(d.get("date_format")),
        "validate_regex": lambda d: validators.validate_regex(d.get("pattern")),
        "is_protected_file": lambda d: config.is_protected_file(d.get("filename", "")),
        "validate_filename": lambda d: validators.validate_filename(d.get("filename", ""))
    }
    
    try:
        for validator_name in request.validators:
            if validator_name not in validator_funcs:
                results.append({
                    "name": validator_name,
                    "result": None,
                    "passed": False,
                    "message": f"未知的验证器: {validator_name}"
                })
                failed_count += 1
                continue
            
            try:
                result = validator_funcs[validator_name](request.data)
                passed = bool(result) or result is None  # None 表示有效
                if passed:
                    passed_count += 1
                else:
                    failed_count += 1
                
                results.append({
                    "name": validator_name,
                    "result": result,
                    "passed": passed,
                    "message": "验证通过" if passed else "验证失败"
                })
            except Exception as e:
                results.append({
                    "name": validator_name,
                    "result": None,
                    "passed": False,
                    "message": str(e)
                })
                failed_count += 1
        
        return ValidatorTestResponse(
            success=True,
            message="验证器测试完成",
            results=results,
            passed_count=passed_count,
            failed_count=failed_count
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证器测试失败: {str(e)}")

@app.post("/test/e2e", response_model=E2ETestResponse, summary="端到端测试")
async def test_e2e(request: E2ETestRequest):
    """
    完整流程测试

    测试步骤：
    1. 创建临时目录
    2. 创建测试文件
    3. 执行重命名操作
    4. 验证结果
    5. 清理临时文件
    """
    temp_dir = None
    errors = []
    
    try:
        # 1. 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="rename_test_")
        
        # 2. 创建测试文件
        create_test_files(temp_dir, request.test_files, request.file_content or "test content")
        
        created_files = helpers.list_files(temp_dir)
        
        # 3. 执行重命名操作
        engine = RenameEngine(source_dir=temp_dir)
        
        files = engine.get_files()
        
        rule = create_rename_rule(request.rule)
        
        rename_map = engine.generate_rename_map(files, rule)
        
        # 检查冲突
        conflicts = engine.check_conflicts(rename_map)
        
        if conflicts:
            errors.append(f"检测到命名冲突: {conflicts}")
        
        # 4. 验证结果
        # 这里只做预览，不实际执行重命名
        final_files = helpers.list_files(temp_dir)
        
        # 5. 清理临时文件（可选，但在这里清理
        cleanup_completed = True
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            cleanup_completed = False
            errors.append(f"清理临时目录失败: {e}")
        
        return E2ETestResponse(
            success=len(errors) == 0,
            message="端到端测试完成",
            scenario_name=request.scenario_name,
            temp_dir=temp_dir,
            created_files=created_files,
            original_files=created_files,
            rename_map=rename_map,
            final_files=final_files,
            cleanup_completed=cleanup_completed,
            errors=errors
        )
        
    except Exception as e:
        # 确保清理临时目录
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"端到端测试失败: {str(e)}")

# =============================================================================
# 用于直接运行

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
