#!/usr/bin/env python3
"""
精确重现 Transport Closed 错误的测试脚本

这个脚本模拟您遇到的具体场景：
- 使用 execute_tooluniverse_function 调用
- 测试长时间运行的工具
- 模拟可能的超时场景
"""

import asyncio
import json
import sys
import time
import traceback
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("❌ MCP 库未安装: pip install mcp")
    sys.exit(1)


async def test_execute_tooluniverse_function():
    """测试 execute_tooluniverse_function 方法"""
    print("=" * 60)
    print("测试 execute_tooluniverse_function 方法")
    print("=" * 60)
    
    # 启动 stdio 服务器
    server = StdioServerParameters(
        command="uv",
        args=["run", "tooluniverse-smcp-stdio", "--no-search"]
    )
    
    try:
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 测试用例 - 使用您遇到的具体参数
                test_cases = [
                    {
                        "name": "OpenTargets_get_drug_description_by_chemblId",
                        "arguments": '{"chemblId":"CHEMBL25"}',
                        "description": "您遇到的第一个失败案例"
                    },
                    {
                        "name": "PubChem_get_CID_by_compound_name", 
                        "arguments": '{"name":"Aspirin"}',
                        "description": "您遇到的第二个失败案例"
                    }
                ]
                
                for i, test_case in enumerate(test_cases):
                    print(f"\n[测试 {i+1}/{len(test_cases)}] {test_case['name']}")
                    print(f"描述: {test_case['description']}")
                    print(f"参数: {test_case['arguments']}")
                    
                    try:
                        start_time = time.time()
                        
                        # 使用 execute_tooluniverse_function 方法
                        result = await session.call_tool(
                            "execute_tooluniverse_function",
                            {
                                "function_name": test_case["name"],
                                "arguments": test_case["arguments"]
                            }
                        )
                        
                        execution_time = time.time() - start_time
                        print(f"✅ 调用成功，耗时 {execution_time:.2f}秒")
                        
                        # 显示结果
                        for content in result.content:
                            print(f"结果: {content.text}")
                            
                    except Exception as e:
                        execution_time = time.time() - start_time
                        error_msg = str(e)
                        
                        print(f"❌ 调用失败，耗时 {execution_time:.2f}秒")
                        print(f"错误: {error_msg}")
                        
                        if "Transport closed" in error_msg:
                            print("🚨 重现了 Transport closed 错误！")
                            
                        # 显示详细错误信息
                        print("\n详细错误信息:")
                        print(traceback.format_exc())
                        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        print(traceback.format_exc())


async def test_direct_tool_calls():
    """测试直接工具调用（对比）"""
    print("\n" + "=" * 60)
    print("测试直接工具调用（对比）")
    print("=" * 60)
    
    server = StdioServerParameters(
        command="uv",
        args=["run", "tooluniverse-smcp-stdio", "--no-search"]
    )
    
    try:
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 测试用例
                test_cases = [
                    {
                        "name": "OpenTargets_get_drug_description_by_chemblId",
                        "args": {"chemblId": "CHEMBL25"}
                    },
                    {
                        "name": "PubChem_get_CID_by_compound_name",
                        "args": {"name": "Aspirin"}
                    }
                ]
                
                for i, test_case in enumerate(test_cases):
                    print(f"\n[测试 {i+1}/{len(test_cases)}] {test_case['name']}")
                    
                    try:
                        start_time = time.time()
                        
                        # 直接调用工具
                        result = await session.call_tool(
                            test_case["name"],
                            test_case["args"]
                        )
                        
                        execution_time = time.time() - start_time
                        print(f"✅ 直接调用成功，耗时 {execution_time:.2f}秒")
                        
                        # 显示结果
                        for content in result.content:
                            print(f"结果: {content.text}")
                            
                    except Exception as e:
                        execution_time = time.time() - start_time
                        error_msg = str(e)
                        
                        print(f"❌ 直接调用失败，耗时 {execution_time:.2f}秒")
                        print(f"错误: {error_msg}")
                        
                        if "Transport closed" in error_msg:
                            print("🚨 重现了 Transport closed 错误！")
                            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        print(traceback.format_exc())


async def test_timeout_scenarios():
    """测试可能的超时场景"""
    print("\n" + "=" * 60)
    print("测试可能的超时场景")
    print("=" * 60)
    
    # 测试一些可能导致超时的工具
    timeout_test_cases = [
        {
            "name": "OpenTargets_get_drug_description_by_chemblId",
            "args": {"chemblId": "CHEMBL25"},
            "description": "GraphQL 查询（无 timeout）"
        },
        {
            "name": "PubChem_get_CID_by_compound_name",
            "args": {"name": "Aspirin"},
            "description": "REST API 查询（30s timeout）"
        },
        # 添加一些可能慢的查询
        {
            "name": "UniProt_search",
            "args": {"query": "protein", "limit": 100},
            "description": "大量结果查询"
        }
    ]
    
    server = StdioServerParameters(
        command="uv",
        args=["run", "tooluniverse-smcp-stdio", "--no-search"]
    )
    
    try:
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                for i, test_case in enumerate(timeout_test_cases):
                    print(f"\n[超时测试 {i+1}/{len(timeout_test_cases)}] {test_case['name']}")
                    print(f"描述: {test_case['description']}")
                    
                    try:
                        start_time = time.time()
                        
                        # 使用 asyncio.wait_for 设置超时
                        result = await asyncio.wait_for(
                            session.call_tool(test_case["name"], test_case["args"]),
                            timeout=30.0  # 30秒超时
                        )
                        
                        execution_time = time.time() - start_time
                        print(f"✅ 调用成功，耗时 {execution_time:.2f}秒")
                        
                        if execution_time > 10:
                            print(f"⚠️ 执行时间较长: {execution_time:.2f}秒")
                            
                    except asyncio.TimeoutError:
                        execution_time = time.time() - start_time
                        print(f"⏰ 调用超时（30秒），实际耗时 {execution_time:.2f}秒")
                        
                    except Exception as e:
                        execution_time = time.time() - start_time
                        error_msg = str(e)
                        
                        print(f"❌ 调用失败，耗时 {execution_time:.2f}秒")
                        print(f"错误: {error_msg}")
                        
                        if "Transport closed" in error_msg:
                            print("🚨 重现了 Transport closed 错误！")
                            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        print(traceback.format_exc())


async def main():
    """主函数"""
    print("开始精确重现 Transport Closed 错误测试")
    print("=" * 80)
    
    try:
        # 测试 1: execute_tooluniverse_function 方法
        await test_execute_tooluniverse_function()
        
        # 测试 2: 直接工具调用
        await test_direct_tool_calls()
        
        # 测试 3: 超时场景
        await test_timeout_scenarios()
        
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        print(traceback.format_exc())
    
    print("\n✨ 测试完成")


if __name__ == "__main__":
    asyncio.run(main())
