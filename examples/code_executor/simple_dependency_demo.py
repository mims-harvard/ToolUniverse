"""
简单的依赖管理演示

这个例子演示 python_script_runner 的依赖管理功能：
1. 运行一个需要缺失包的脚本
2. 系统检测到缺失的包
3. 提示用户是否安装
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
    """简单的依赖管理演示"""
    print("=" * 60)
    print("python_script_runner 依赖管理演示")
    print("=" * 60)
    
    # 初始化 ToolUniverse
    client = ToolUniverse()
    client.load_tools(['python_executor'])
    
    # 创建一个需要缺失包的脚本
    script_content = '''
# 这个脚本需要 keggtools.api 子模块（不存在的子模块）
try:
    import keggtools.api
    print("✅ keggtools.api 子模块已安装")
    result = "成功导入 keggtools.api"
except ImportError as e:
    print(f"❌ keggtools.api 子模块未安装: {e}")
    result = "keggtools.api 子模块缺失"

print(f"结果: {result}")
'''
    
    # 创建临时脚本文件
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = os.path.join(temp_dir, "test_dependency.py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        print(f"📝 创建测试脚本: {script_path}")
        print(f"📦 脚本需要: keggtools.api 子模块（不存在的子模块）")
        
        # 运行脚本，指定依赖并需要用户确认
        print(f"\n🔍 运行脚本并检查依赖...")
        
        result = client.run_one_function({
            "name": "python_script_runner",
            "arguments": {
                "script_path": script_path,
                "dependencies": ["keggtools.api"],  # 指定需要的子模块
                "auto_install_dependencies": False,  # 不自动安装
                "require_confirmation": True,  # 需要用户确认
                "timeout": 30
            }
        })
        
        print(f"\n📋 执行结果:")
        print(f"   成功: {result.get('success', False)}")
        
        if result.get("success"):
            print(f"   ✅ 脚本执行成功")
            print(f"   📤 输出: {result.get('stdout', '')}")
        elif result.get("requires_confirmation"):
            print(f"   🔐 需要用户确认安装包")
            print(f"   📦 缺失的包: {result.get('missing_packages', [])}")
            print(f"   💻 安装命令: {result.get('install_command', '')}")
            print(f"\n💡 要安装这些包，请运行:")
            print(f"   {result.get('install_command', '')}")
        else:
            print(f"   ❌ 执行失败: {result.get('error', '未知错误')}")
    
    print(f"\n🎉 演示完成！")
    print(f"   这个例子展示了:")
    print(f"   • 自动检测缺失的包")
    print(f"   • 提示用户确认安装")
    print(f"   • 提供安装命令")


if __name__ == "__main__":
    main()
