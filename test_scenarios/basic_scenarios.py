"""
基础测试场景配置
"""
from typing import List, Dict, Any

# 基础场景测试用例
BASIC_TEST_SCENARIOS = {
    "prefix_test: {
        "name": "添加前缀测试",
        "rule": {
            "prefix": "IMG_"
        },
        "test_files": ["photo.jpg", "document.txt", "image.png"],
        "expected": ["IMG_photo.jpg", "IMG_document.txt", "IMG_image.png"]
    },
    "suffix_test": {
        "name": "添加后缀测试",
        "rule": {
            "suffix": "_2025"
        },
        "test_files": ["photo.jpg", "document.txt", "image.png"],
        "expected": ["photo_2025.jpg", "document_2025.txt", "image_2025.png"]
    },
    "replace_test": {
        "name": "字符串替换测试",
        "rule": {
            "replace": "photo,image"
        },
        "test_files": ["photo.jpg", "photo_001.jpg", "my_photo.png"],
        "expected": ["image.jpg", "image_001.jpg", "my_image.png"]
    },
    "numbering_test": {
        "name": "序号格式化测试",
        "rule": {
            "number_start": 1,
            "padding": 3
        },
        "test_files": ["a.jpg", "b.txt", "c.png"],
        "expected": ["001_a.jpg", "002_b.txt", "003_c.png"]
    }
}

# 边界场景测试用例
EDGE_TEST_SCENARIOS = {
    "empty_directory": {
        "name": "空目录测试",
        "rule": {
            "prefix": "TEST_"
        },
        "test_files": [],
        "expected": []
    },
    "no_extension_match": {
        "name": "无匹配扩展名测试",
        "rule": {
            "prefix": "DOC_"
        },
        "extensions": [".docx", ".doc"],
        "test_files": ["photo.jpg", "image.png"],
        "expected": []
    },
    "name_conflict": {
        "name": "文件名冲突测试",
        "rename_map": {
            "file1.jpg": "output.jpg",
            "file2.jpg": "output.jpg"
        },
        "expected_conflicts": ["output.jpg"]
    },
    "protected_file_access": {
        "name": "受保护文件访问测试",
        "test_files": [".do_not_touch.cfg", "normal_file.txt"],
        "expected": []
    }
}

# 复杂场景测试用例
COMPLEX_TEST_SCENARIOS = {
    "combined_rules": {
        "name": "组合多种规则测试",
        "rule": {
            "prefix": "PRE_",
            "suffix": "_END",
            "replace": "test,demo"
        },
        "test_files": ["test_file_01.txt", "test_file_02.txt"],
        "expected": ["PRE__file_01_END.txt", "PRE__file_02_END.txt"]
    },
    "regex_replace": {
        "name": "正则表达式替换测试",
        "rule": {
            "regex": r"photo_(\d+),img_$1"
        },
        "test_files": ["photo_001.jpg", "photo_002.jpg"],
        "expected": ["img_001.jpg", "img_002.jpg"]
    },
    "date_format": {
        "name": "日期格式化插入测试",
        "rule": {
            "date_format": "%Y%m%d"
        },
        "test_files": ["document.txt"],
        "expected": ["document_20250328.txt"]
    }
}

# API 测试请求示例
API_TEST_EXAMPLES = {
    "rule_test": {
        "summary": "测试前缀规则",
        "value": {
            "rule": {
                "prefix": "TEST_"
            },
            "test_files": ["file1.jpg", "file2.txt"]
        }
    },
    "engine_test": {
        "summary": "测试完整重命名流程",
        "value": {
            "rule": {
                "prefix": "IMG_",
                "number_start": 1,
                "padding": 3
            },
            "extensions": ["jpg", "png"]
        }
    },
    "conflict_test": {
        "summary": "测试命名冲突",
        "value": {
            "rename_map": {
                "a.jpg": "output.jpg",
                "b.jpg": "output.jpg"
            }
        }
    },
    "validator_test": {
        "summary": "测试目录验证",
        "value": {
            "validators": ["validate_source_dir"],
            "data": {
                "path": "./source_data/"
            }
        }
    },
    "e2e_test": {
        "summary": "端到端测试",
        "value": {
            "scenario_name": "complete_workflow",
            "rule": {
                "prefix": "E2E_",
                "number_start": 1,
                "padding": 3
            },
            "test_files": ["test1.txt", "test2.txt"]
        }
    }
}
