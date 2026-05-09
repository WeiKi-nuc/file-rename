"""
快速测试API的脚本
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_rule_endpoint():
    """测试规则测试接口"""
    url = f"{BASE_URL}/test/rule"
    payload = {
        "rule": {"prefix": "TEST_"},
        "test_files": ["file1.jpg", "file2.txt", "photo.png"]
    }
    response = requests.post(url, json=payload)
    print("=== 测试 /test/rule ===")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"错误: {response.text}")
    return response.status_code == 200

def test_validators_endpoint():
    """测试验证器接口"""
    url = f"{BASE_URL}/test/validators"
    payload = {
        "validators": ["validate_source_dir", "is_protected_file"],
        "data": {
            "path": "./source_data/",
            "filename": ".do_not_touch.cfg"
        }
    }
    response = requests.post(url, json=payload)
    print("\n=== 测试 /test/validators ===")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"错误: {response.text}")
    return response.status_code == 200

def test_conflicts_endpoint():
    """测试冲突检测接口"""
    url = f"{BASE_URL}/test/conflicts"
    payload = {
        "rename_map": {
            "file1.jpg": "output.jpg",
            "file2.txt": "output.jpg"
        }
    }
    response = requests.post(url, json=payload)
    print("\n=== 测试 /test/conflicts ===")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"错误: {response.text}")
    return response.status_code == 200

def test_e2e_endpoint():
    """测试端到端接口"""
    url = f"{BASE_URL}/test/e2e"
    payload = {
        "scenario_name": "test_workflow",
        "rule": {
            "prefix": "E2E_",
            "number_start": 1,
            "padding": 3
        },
        "test_files": ["test_a.txt", "test_b.txt"]
    }
    response = requests.post(url, json=payload)
    print("\n=== 测试 /test/e2e ===")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"错误: {response.text}")
    return response.status_code == 200

if __name__ == "__main__":
    print("开始测试 FastAPI 测试接口...\n")
    
    results = []
    results.append(("规则测试接口", test_rule_endpoint()))
    results.append(("验证器测试接口", test_validators_endpoint()))
    results.append(("冲突检测接口", test_conflicts_endpoint()))
    results.append(("端到端测试接口", test_e2e_endpoint()))
    
    print("\n" + "="*50)
    print("测试结果汇总:")
    print("="*50)
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name}: {status}")
    print("="*50)
