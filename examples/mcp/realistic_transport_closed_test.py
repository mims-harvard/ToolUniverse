#!/usr/bin/env python3
"""
模拟真实使用场景的 Transport Closed 测试

这个脚本模拟您可能遇到的具体使用场景：
1. 使用真实的 MCP 客户端调用方式
2. 模拟网络延迟和超时
3. 测试不同的超时设置
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


async def test_with_different_timeouts():
    """测试不同的超时设置"""
    print("=" * 60)
    print("测试不同的超时设置")
    print("=" * 60)
    
    # 测试不同的超时时间
    timeout_tests = [
        {"timeout": 1.0, "description": "1秒超时（很严格）"},
        {"timeout": 2.0, "description": "2秒超时（严格）"},
        {"timeout": 5.0, "description": "5秒超时（中等）"},
        {"timeout": 10.0, "description": "10秒超时（宽松）"},
        {"timeout": 30.0, "description": "30秒超时（很宽松）"}
    ]
    
    test_cases = [
        {
            "name": "OpenTargets_get_drug_description_by_chemblId",
            "args": {"chemblId": "CHEMBL25"},
            "description": "您遇到的第一个失败案例"
        },
        {
            "name": "PubChem_get_CID_by_compound_name",
            "args": {"name": "Aspirin"},
            "description": "您遇到的第二个失败案例"
        }
    ]
    
    for timeout_test in timeout_tests:
        print(f"\n--- {timeout_test['description']} ---")
        
        server = StdioServerParameters(
            command="uv",
            args=["run", "tooluniverse-smcp-stdio", "--no-search"]
        )
        
        try:
            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    for test_case in test_cases:
                        print(f"\n测试: {test_case['name']}")
                        print(f"描述: {test_case['description']}")
                        
                        try:
                            start_time = time.time()
                            
                            # 使用指定的超时时间
                            result = await asyncio.wait_for(
                                session.call_tool(test_case["name"], test_case["args"]),
                                timeout=timeout_test["timeout"]
                            )
                            
                            execution_time = time.time() - start_time
                            print(f"✅ 成功，耗时 {execution_time:.2f}秒")
                            
                        except asyncio.TimeoutError:
                            execution_time = time.time() - start_time
                            print(f"⏰ 超时（{timeout_test['timeout']}秒），实际耗时 {execution_time:.2f}秒")
                            
                        except Exception as e:
                            execution_time = time.time() - start_time
                            error_msg = str(e)
                            
                            print(f"❌ 失败，耗时 {execution_time:.2f}秒")
                            print(f"错误: {error_msg}")
                            
                            if "Transport closed" in error_msg:
                                print("🚨 重现了 Transport closed 错误！")
                                return True
                                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 服务器异常: {error_msg}")
            
            if "Transport closed" in error_msg:
                print("🚨 重现了 Transport closed 错误！")
                return True
                
    return False


async def test_with_execute_tooluniverse_function():
    """使用 execute_tooluniverse_function 方法测试"""
    print("\n" + "=" * 60)
    print("使用 execute_tooluniverse_function 方法测试")
    print("=" * 60)
    
    test_cases = [
        {
            "function_name": "OpenTargets_get_drug_description_by_chemblId",
            "arguments": '{"chemblId":"CHEMBL25"}',
            "description": "您遇到的第一个失败案例"
        },
        {
            "function_name": "PubChem_get_CID_by_compound_name",
            "arguments": '{"name":"Aspirin"}',
            "description": "您遇到的第二个失败案例"
        }
    ]
    
    # 测试不同的超时设置
    timeouts = [1.0, 2.0, 5.0, 10.0, 30.0]
    
    for timeout in timeouts:
        print(f"\n--- 超时设置: {timeout}秒 ---")
        
        server = StdioServerParameters(
            command="uv",
            args=["run", "tooluniverse-smcp-stdio", "--no-search"]
        )
        
        try:
            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    for test_case in test_cases:
                        print(f"\n测试: {test_case['function_name']}")
                        print(f"描述: {test_case['description']}")
                        print(f"参数: {test_case['arguments']}")
                        
                        try:
                            start_time = time.time()
                            
                            # 使用 execute_tooluniverse_function 方法
                            result = await asyncio.wait_for(
                                session.call_tool(
                                    "execute_tooluniverse_function",
                                    {
                                        "function_name": test_case["function_name"],
                                        "arguments": test_case["arguments"]
                                    }
                                ),
                                timeout=timeout
                            )
                            
                            execution_time = time.time() - start_time
                            print(f"✅ 成功，耗时 {execution_time:.2f}秒")
                            
                            # 显示结果
                            for content in result.content:
                                print(f"结果: {content.text}")
                                
                        except asyncio.TimeoutError:
                            execution_time = time.time() - start_time
                            print(f"⏰ 超时（{timeout}秒），实际耗时 {execution_time:.2f}秒")
                            
                        except Exception as e:
                            execution_time = time.time() - start_time
                            error_msg = str(e)
                            
                            print(f"❌ 失败，耗时 {execution_time:.2f}秒")
                            print(f"错误: {error_msg}")
                            
                            if "Transport closed" in error_msg:
                                print("🚨 重现了 Transport closed 错误！")
                                return True
                                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 服务器异常: {error_msg}")
            
            if "Transport closed" in error_msg:
                print("🚨 重现了 Transport closed 错误！")
                return True
                
    return False


async def test_with_network_delay_simulation():
    """模拟网络延迟"""
    print("\n" + "=" * 60)
    print("模拟网络延迟")
    print("=" * 60)
    
    # 通过多次快速调用来模拟网络不稳定
    server = StdioServerParameters(
        command="uv",
        args=["run", "tooluniverse-smcp-stdio", "--no-search"]
    )
    
    try:
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 快速连续调用，模拟网络不稳定
                for i in range(20):
                    print(f"\n快速调用 {i+1}/20")
                    
                    try:
                        start_time = time.time()
                        
                        # 使用很短的超时
                        result = await asyncio.wait_for(
                            session.call_tool("OpenTargets_get_drug_description_by_chemblId", 
                                            {"chemblId": "CHEMBL25"}),
                            timeout=1.0
                        )
                        
                        execution_time = time.time() - start_time
                        print(f"✅ 成功，耗时 {execution_time:.2f}秒")
                        
                        # 短暂延迟
                        await asyncio.sleep(0.1)
                        
                    except asyncio.TimeoutError:
                        execution_time = time.time() - start_time
                        print(f"⏰ 超时（1秒），实际耗时 {execution_time:.2f}秒")
                        
                    except Exception as e:
                        execution_time = time.time() - start_time
                        error_msg = str(e)
                        
                        print(f"❌ 失败，耗时 {execution_time:.2f}秒")
                        print(f"错误: {error_msg}")
                        
                        if "Transport closed" in error_msg:
                            print("🚨 重现了 Transport closed 错误！")
                            return True
                            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 网络延迟测试异常: {error_msg}")
        
        if "Transport closed" in error_msg:
            print("🚨 重现了 Transport closed 错误！")
            return True
            
    return False


async def test_with_process_interruption():
    """测试进程中断场景"""
    print("\n" + "=" * 60)
    print("测试进程中断场景")
    print("=" * 60)
    
    server = StdioServerParameters(
        command="uv",
        args=["run", "tooluniverse-smcp-stdio", "--no-search"]
    )
    
    try:
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 启动一个任务
                task = asyncio.create_task(
                    session.call_tool("OpenTargets_get_drug_description_by_chemblId", 
                                    {"chemblId": "CHEMBL25"})
                )
                
                # 立即取消任务
                task.cancel()
                
                try:
                    result = await task
                    print("✅ 任务完成")
                except asyncio.CancelledError:
                    print("⚠️ 任务被取消")
                    
                    # 尝试再次调用
                    try:
                        start_time = time.time()
                        result = await asyncio.wait_for(
                            session.call_tool("PubChem_get_CID_by_compound_name", 
                                            {"name": "Aspirin"}),
                            timeout=5.0
                        )
                        execution_time = time.time() - start_time
                        print(f"✅ 后续调用成功，耗时 {execution_time:.2f}秒")
                        
                    except Exception as e:
                        execution_time = time.time() - start_time
                        error_msg = str(e)
                        
                        print(f"❌ 后续调用失败，耗时 {execution_time:.2f}秒")
                        print(f"错误: {error_msg}")
                        
                        if "Transport closed" in error_msg:
                            print("🚨 重现了 Transport closed 错误！")
                            return True
                            
                except Exception as e:
                    error_msg = str(e)
                    print(f"❌ 任务异常: {error_msg}")
                    
                    if "Transport closed" in error_msg:
                        print("🚨 重现了 Transport closed 错误！")
                        return True
                        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 进程中断测试异常: {error_msg}")
        
        if "Transport closed" in error_msg:
            print("🚨 重现了 Transport closed 错误！")
            return True
            
    return False


async def main():
    """主函数"""
    print("开始模拟真实使用场景的 Transport Closed 测试")
    print("=" * 80)
    
    try:
        # 测试 1: 不同超时设置
        if await test_with_different_timeouts():
            print("\n🎯 通过不同超时设置测试重现了 Transport closed 错误！")
            return
            
        # 测试 2: execute_tooluniverse_function 方法
        if await test_with_execute_tooluniverse_function():
            print("\n🎯 通过 execute_tooluniverse_function 测试重现了 Transport closed 错误！")
            return
            
        # 测试 3: 网络延迟模拟
        if await test_with_network_delay_simulation():
            print("\n🎯 通过网络延迟模拟测试重现了 Transport closed 错误！")
            return
            
        # 测试 4: 进程中断场景
        if await test_with_process_interruption():
            print("\n🎯 通过进程中断场景测试重现了 Transport closed 错误！")
            return
            
        print("\n❌ 未能重现 Transport closed 错误")
        print("\n💡 建议:")
        print("1. 检查您的 MCP 客户端超时设置")
        print("2. 尝试使用 HTTP 传输而不是 stdio")
        print("3. 检查网络连接和 API 访问速度")
        print("4. 考虑为 GraphQL 工具添加 timeout 参数")
        
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        print(traceback.format_exc())
    
    print("\n✨ 测试完成")


if __name__ == "__main__":
    asyncio.run(main())
