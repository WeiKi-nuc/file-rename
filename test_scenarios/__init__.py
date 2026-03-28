"""
测试场景配置包

包含以下测试场景配置文件：
- basic_scenarios.json: 基础测试场景
- edge_cases.json: 边界测试场景
- complex_scenarios.json: 复杂测试场景
- validator_tests.json: 验证器测试场景

使用方法：
    from test_scenarios import load_scenario
    scenarios = load_scenario('basic_scenarios.json')
"""

import json
import os
from typing import Dict, Any, Optional


def load_scenario(filename: str) -> Optional[Dict[str, Any]]:
    """
    加载测试场景配置文件
    
    Args:
        filename: 场景文件名
        
    Returns:
        场景配置字典，失败返回 None
    """
    try:
        filepath = os.path.join(os.path.dirname(__file__), filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def list_scenarios() -> list:
    """
    列出所有可用的场景文件
    
    Returns:
        场景文件名列表
    """
    scenario_dir = os.path.dirname(__file__)
    return [f for f in os.listdir(scenario_dir) if f.endswith('.json')]


def get_all_scenarios() -> Dict[str, Dict[str, Any]]:
    """
    加载所有测试场景
    
    Returns:
        {文件名: 场景配置} 字典
    """
    all_scenarios = {}
    for filename in list_scenarios():
        scenario = load_scenario(filename)
        if scenario:
            all_scenarios[filename] = scenario
    return all_scenarios
