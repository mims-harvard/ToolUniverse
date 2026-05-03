"""
直接演示 python_script_runner 依赖管理功能
"""

import tempfile
import os
import sys
from pathlib import Path

# Add src to path
current_dir = Path(__file__).parent
src_path = current_dir.parent.parent / "src"
sys.path.insert(0, str(src_path))

from tooluniverse import ToolUniverse


def main():
    """直接演示依赖管理功能"""
    # 初始化
    client = ToolUniverse()
    client.load_tools(['python_executor'])
    
    # 创建需要缺失包的脚本
    script_content = '''
import nonexistent_package_12345
print("包导入成功")
'''
    
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = os.path.join(temp_dir, "test.py")
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # 运行脚本
        result = client.run_one_function({
            "name": "python_script_runner",
            "arguments": {
                "script_path": script_path,
                "dependencies": ["nonexistent_package_12345"],
                "auto_install_dependencies": False,
                "require_confirmation": True,
                "timeout": 30
            }
        })
        
        # 直接输出结果
        print(result)


if __name__ == "__main__":
    main()
