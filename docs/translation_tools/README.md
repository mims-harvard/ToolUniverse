# Translation Tools

这个文件夹包含了基于 ToolUniverse AgenticTool 的翻译工具，用于批量翻译 .po 文件。

## 文件说明

### 核心文件

- **`batch_translate_po.py`** - 主要的批量翻译脚本
 - 命令行界面，易于使用
 - 支持单个文件和批量翻译
 - 翻译状态查看和统计
 - 可配置的翻译参数

- **`translation_agentic_tool.py`** - 完整的演示脚本
 - 展示如何使用 AgenticTool
 - 包含完整的类实现示例
 - 适合学习和理解 AgenticTool 用法

- **`AGENTIC_TRANSLATION_TOOL_SUMMARY.md`** - 完整的实现总结
 - 详细的技术实现说明
 - 使用方法和示例
 - 测试结果和性能分析

## 快速开始

### 安装依赖

```bash
pip install polib openai
```

### 基本使用

```bash
# 查看翻译状态
python batch_translate_po.py --status

# 翻译单个文件
python batch_translate_po.py --file path/to/file.po

# 批量翻译目录
python batch_translate_po.py --directory path/to/po/files
```

### 高级选项

```bash
# 使用自定义参数
python batch_translate_po.py \
   --directory locale/zh_CN/LC_MESSAGES \
   --max-entries 50 \
   --model gpt-4o-mini \
   --temperature 0.3
```

## 特点

-  无需修改源代码，完全在 docs 目录下实现
-  基于 ToolUniverse AgenticTool 框架
-  智能翻译，保持技术术语一致性
-  支持大规模批量处理
-  详细的错误处理和日志记录
-  用户友好的命令行界面

## 技术实现

这个翻译工具展示了如何在不修改 ToolUniverse 源代码的情况下，利用其 AgenticTool 功能来构建强大的翻译工具。它使用 LLM 进行高质量的翻译，并提供了完整的批量处理功能。
