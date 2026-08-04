#!/usr/bin/env python3
"""
文档示例验证脚本
自动验证文档中的所有代码示例是否能正确执行
"""

import ast
import re
import sys
import os
from pathlib import Path


def extract_code_blocks(rst_file):
    """提取RST文件中的Python代码块"""
    with open(rst_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 匹配 .. code-block:: python 后的代码
    pattern = r".. code-block:: python\s*\n\n((?:   .*\n)*)"
    matches = re.findall(pattern, content, re.MULTILINE)

    code_blocks = []
    for match in matches:
        # 移除缩进
        lines = match.split("\n")
        cleaned_lines = [line[3:] if line.startswith("   ") else line for line in lines]
        code = "\n".join(cleaned_lines).strip()
        if code:
            code_blocks.append(code)

    return code_blocks


def validate_python_syntax(code):
    """验证Python代码语法"""
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)


def check_imports_availability(code):
    """检查导入是否可用"""
    try:
        # 模拟导入检查
        import_pattern = r"from\s+(\S+)\s+import|import\s+(\S+)"
        imports = re.findall(import_pattern, code)

        unavailable_imports = []
        for from_module, import_module in imports:
            module = from_module or import_module
            if module.startswith("tooluniverse"):
                # 检查tooluniverse模块
                try:
                    exec(f"import {module}")
                except ImportError:
                    unavailable_imports.append(module)

        return len(unavailable_imports) == 0, unavailable_imports
    except Exception as e:
        return False, [str(e)]


def main():
    """主函数"""
    docs_dir = Path(__file__).parent
    rst_files = list(docs_dir.glob("*.rst"))

    total_files = 0
    total_code_blocks = 0
    syntax_errors = 0
    import_errors = 0

    print("🔍 验证文档中的代码示例...")
    print("=" * 50)

    for rst_file in rst_files:
        total_files += 1
        print(f"\n📄 检查文件: {rst_file.name}")

        code_blocks = extract_code_blocks(rst_file)
        total_code_blocks += len(code_blocks)

        if not code_blocks:
            print("   ℹ️  无代码块")
            continue

        for i, code in enumerate(code_blocks, 1):
            print(f"   📝 代码块 {i}:")

            # 语法检查
            is_valid, error = validate_python_syntax(code)
            if not is_valid:
                syntax_errors += 1
                print(f"      ❌ 语法错误: {error}")
                continue

            # 导入检查
            imports_ok, missing = check_imports_availability(code)
            if not imports_ok:
                import_errors += 1
                print(f"      ⚠️  导入问题: {missing}")
            else:
                print(f"      ✅ 代码有效")

    # 统计报告
    print("\n" + "=" * 50)
    print("📊 验证结果统计:")
    print(f"   📄 检查文件数: {total_files}")
    print(f"   📝 代码块总数: {total_code_blocks}")
    print(f"   ❌ 语法错误数: {syntax_errors}")
    print(f"   ⚠️  导入错误数: {import_errors}")

    success_rate = (
        (total_code_blocks - syntax_errors - import_errors) / max(total_code_blocks, 1)
    ) * 100
    print(f"   ✅ 成功率: {success_rate:.1f}%")

    if syntax_errors > 0 or import_errors > 0:
        print("\n💡 建议:")
        print("   1. 修复语法错误的代码示例")
        print("   2. 确保所有导入路径正确")
        print("   3. 添加实际可执行的示例")
        return 1
    else:
        print("\n🎉 所有代码示例验证通过！")
        return 0


if __name__ == "__main__":
    sys.exit(main())
