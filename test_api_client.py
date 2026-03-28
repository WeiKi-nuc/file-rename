"""
测试 API 客户端 - 用于验证测试服务
"""
import requests
import json

base_url = 'http://127.0.0.1:8002'

def test_root():
    """测试根路径"""
    print('=== 根路径 ===')
    r = requests.get(f'{base_url}/')
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))

def test_health():
    """测试健康检查"""
    print('\n=== 健康检查 ===')
    r = requests.get(f'{base_url}/health')
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))

def test_rule():
    """测试规则接口"""
    print('\n=== 1. 规则测试接口 (/test/rule) ===')
    r = requests.post(f'{base_url}/test/rule', json={
        'prefix': 'TEST_',
        'suffix': '_v1',
        'test_files': ['file1.txt', 'file2.txt', 'photo.jpg']
    })
    result = r.json()
    print(f"状态码: {r.status_code}")
    if r.status_code == 200:
        print(f"成功: {result['success']}")
        print(f"消息: {result['message']}")
        print(f"文件数: {result['total_files']}")
        print('重命名结果:')
        for item in result['results'][:3]:
            print(f"  {item['original']} -> {item['new']} (改变: {item['changed']})")
    else:
        print(f"错误: {result}")

def test_validators():
    """测试验证器接口"""
    print('\n=== 2. 验证器测试接口 (/test/validators) ===')
    r = requests.post(f'{base_url}/test/validators', json={
        'test_type': 'extensions',
        'test_value': 'jpg,png,gif'
    })
    result = r.json()
    print(f"状态码: {r.status_code}")
    print(f"类型: {result['test_type']}")
    print(f"输入: {result['input_value']}")
    print(f"结果: {result['result']}")
    print(f"是否有效: {result['is_valid']}")

def test_conflicts():
    """测试冲突检测接口"""
    print('\n=== 3. 冲突检测接口 (/test/conflicts) ===')
    r = requests.post(f'{base_url}/test/conflicts', json={
        'rename_mapping': {
            'file1.txt': 'new_name.txt',
            'file2.txt': 'new_name.txt',
            'file3.txt': 'unique.txt'
        }
    })
    result = r.json()
    print(f"状态码: {r.status_code}")
    print(f"有冲突: {result['has_conflicts']}")
    print(f"冲突数: {result['conflict_count']}")
    print(f"冲突详情: {result['conflicts']}")

def test_engine():
    """测试引擎接口"""
    print('\n=== 4. 引擎测试接口 (/test/engine) ===')
    r = requests.post(f'{base_url}/test/engine', json={
        'prefix': 'TEST_',
        'number_start': 1,
        'padding': 3
    })
    result = r.json()
    print(f"状态码: {r.status_code}")
    print(f"成功: {result['success']}")
    print(f"消息: {result['message']}")
    print(f"找到文件: {result['files_found']}")
    print(f"统计: {result['stats']}")

def test_e2e():
    """测试端到端接口"""
    print('\n=== 5. 端到端测试接口 (/test/e2e) ===')
    r = requests.post(f'{base_url}/test/e2e', json={
        'scenarios': [
            {
                'name': '快速测试',
                'description': '简单的前缀测试',
                'create_files': ['test1.txt', 'test2.txt'],
                'rule': {'prefix': 'NEW_', 'number_start': 1, 'padding': 2}
            }
        ],
        'auto_cleanup': True
    })
    result = r.json()
    print(f"状态码: {r.status_code}")
    print(f"成功: {result['success']}")
    print(f"消息: {result['message']}")
    print(f"总场景: {result['total_scenarios']}")
    print(f"通过: {result['passed']}, 失败: {result['failed']}")

if __name__ == '__main__':
    test_root()
    test_health()
    test_rule()
    test_validators()
    test_conflicts()
    test_engine()
    test_e2e()
    print('\n所有测试完成!')
