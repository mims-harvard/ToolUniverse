#!/usr/bin/env python3
"""
强制重现 Transport Closed 错误的测试脚本

这个脚本通过以下方式尝试重现问题：
1. 模拟网络延迟和超时
2. 使用可能导致长时间响应的查询
3. 测试并发调用
4. 模拟资源限制场景
"""

import asyncio
import json
import sys
import time
import traceback
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, List
import signal
import os

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("❌ MCP 库未安装: pip install mcp")
    sys.exit(1)


class TransportClosedReproducer:
    """Transport Closed 错误重现器"""
    
    def __init__(self):
        self.results = []
        
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    async def test_slow_queries(self):
        """测试可能导致长时间响应的查询"""
        self.log("=" * 60)
        self.log("测试可能导致长时间响应的查询")
        self.log("=" * 60)
        
        # 一些可能导致长时间响应的查询
        slow_queries = [
            {
                "name": "OpenTargets_get_drug_description_by_chemblId",
                "args": {"chemblId": "CHEMBL1"},  # 使用一个可能不存在的ID
                "description": "不存在的 ChEMBL ID"
            },
            {
                "name": "OpenTargets_get_drug_description_by_chemblId", 
                "args": {"chemblId": "CHEMBL999999"},  # 明显不存在的ID
                "description": "明显不存在的 ChEMBL ID"
            },
            {
                "name": "PubChem_get_CID_by_compound_name",
                "args": {"name": "very_long_compound_name_that_does_not_exist_12345"},
                "description": "不存在的化合物名称"
            },
            {
                "name": "UniProt_search",
                "args": {"query": "very_specific_and_long_query_that_might_take_time", "limit": 1000},
                "description": "大量结果的查询"
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
                    
                    for i, query in enumerate(slow_queries):
                        self.log(f"\n[慢查询测试 {i+1}/{len(slow_queries)}] {query['name']}")
                        self.log(f"描述: {query['description']}")
                        self.log(f"参数: {query['args']}")
                        
                        try:
                            start_time = time.time()
                            
                            # 使用较短的超时来强制触发超时
                            result = await asyncio.wait_for(
                                session.call_tool(query["name"], query["args"]),
                                timeout=5.0  # 5秒超时
                            )
                            
                            execution_time = time.time() - start_time
                            self.log(f"✅ 查询成功，耗时 {execution_time:.2f}秒")
                            
                        except asyncio.TimeoutError:
                            execution_time = time.time() - start_time
                            self.log(f"⏰ 查询超时（5秒），实际耗时 {execution_time:.2f}秒")
                            
                        except Exception as e:
                            execution_time = time.time() - start_time
                            error_msg = str(e)
                            
                            self.log(f"❌ 查询失败，耗时 {execution_time:.2f}秒")
                            self.log(f"错误: {error_msg}")
                            
                            if "Transport closed" in error_msg:
                                self.log("🚨 重现了 Transport closed 错误！", "ERROR")
                                return True
                                
        except Exception as e:
            self.log(f"❌ 测试异常: {e}", "ERROR")
            if "Transport closed" in str(e):
                self.log("🚨 重现了 Transport closed 错误！", "ERROR")
                return True
                
        return False
    
    async def test_concurrent_calls(self):
        """测试并发调用"""
        self.log("\n" + "=" * 60)
        self.log("测试并发调用")
        self.log("=" * 60)
        
        server = StdioServerParameters(
            command="uv",
            args=["run", "tooluniverse-smcp-stdio", "--no-search"]
        )
        
        try:
            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # 并发调用多个工具
                    tasks = []
                    
                    # 创建多个并发任务
                    for i in range(5):
                        task = asyncio.create_task(
                            session.call_tool("OpenTargets_get_drug_description_by_chemblId", 
                                            {"chemblId": f"CHEMBL{i+1}"})
                        )
                        tasks.append(task)
                    
                    for i in range(3):
                        task = asyncio.create_task(
                            session.call_tool("PubChem_get_CID_by_compound_name", 
                                            {"name": f"compound_{i}"})
                        )
                        tasks.append(task)
                    
                    self.log(f"启动 {len(tasks)} 个并发调用...")
                    
                    try:
                        start_time = time.time()
                        results = await asyncio.wait_for(
                            asyncio.gather(*tasks, return_exceptions=True),
                            timeout=30.0
                        )
                        execution_time = time.time() - start_time
                        
                        self.log(f"✅ 并发调用完成，总耗时 {execution_time:.2f}秒")
                        
                        # 检查结果
                        for i, result in enumerate(results):
                            if isinstance(result, Exception):
                                error_msg = str(result)
                                self.log(f"任务 {i+1} 失败: {error_msg}")
                                if "Transport closed" in error_msg:
                                    self.log("🚨 重现了 Transport closed 错误！", "ERROR")
                                    return True
                            else:
                                self.log(f"任务 {i+1} 成功")
                                
                    except asyncio.TimeoutError:
                        execution_time = time.time() - start_time
                        self.log(f"⏰ 并发调用超时（30秒），实际耗时 {execution_time:.2f}秒")
                        
        except Exception as e:
            self.log(f"❌ 并发测试异常: {e}", "ERROR")
            if "Transport closed" in str(e):
                self.log("🚨 重现了 Transport closed 错误！", "ERROR")
                return True
                
        return False
    
    async def test_resource_stress(self):
        """测试资源压力场景"""
        self.log("\n" + "=" * 60)
        self.log("测试资源压力场景")
        self.log("=" * 60)
        
        # 限制系统资源
        original_limit = None
        try:
            import resource
            # 设置内存限制
            original_limit = resource.getrlimit(resource.RLIMIT_AS)
            resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, original_limit[1]))  # 100MB
            self.log("设置内存限制为 100MB")
        except Exception as e:
            self.log(f"无法设置资源限制: {e}")
        
        try:
            server = StdioServerParameters(
                command="uv",
                args=["run", "tooluniverse-smcp-stdio", "--no-search", "--max-workers", "1"]
            )
            
            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # 在资源限制下进行大量调用
                    for i in range(10):
                        self.log(f"资源压力测试 {i+1}/10")
                        
                        try:
                            start_time = time.time()
                            
                            result = await asyncio.wait_for(
                                session.call_tool("OpenTargets_get_drug_description_by_chemblId", 
                                                {"chemblId": f"CHEMBL{i+10}"}),
                                timeout=10.0
                            )
                            
                            execution_time = time.time() - start_time
                            self.log(f"✅ 调用成功，耗时 {execution_time:.2f}秒")
                            
                        except asyncio.TimeoutError:
                            execution_time = time.time() - start_time
                            self.log(f"⏰ 调用超时（10秒），实际耗时 {execution_time:.2f}秒")
                            
                        except Exception as e:
                            execution_time = time.time() - start_time
                            error_msg = str(e)
                            
                            self.log(f"❌ 调用失败，耗时 {execution_time:.2f}秒")
                            self.log(f"错误: {error_msg}")
                            
                            if "Transport closed" in error_msg:
                                self.log("🚨 重现了 Transport closed 错误！", "ERROR")
                                return True
                                
        except Exception as e:
            self.log(f"❌ 资源压力测试异常: {e}", "ERROR")
            if "Transport closed" in str(e):
                self.log("🚨 重现了 Transport closed 错误！", "ERROR")
                return True
        finally:
            # 恢复资源限制
            if original_limit:
                try:
                    resource.setrlimit(resource.RLIMIT_AS, original_limit)
                    self.log("恢复原始资源限制")
                except Exception as e:
                    self.log(f"无法恢复资源限制: {e}")
                    
        return False
    
    async def test_network_simulation(self):
        """模拟网络问题"""
        self.log("\n" + "=" * 60)
        self.log("模拟网络问题")
        self.log("=" * 60)
        
        # 通过修改系统时间或使用代理来模拟网络延迟
        # 这里我们使用一个更直接的方法：强制使用可能导致超时的查询
        
        problematic_queries = [
            {
                "name": "OpenTargets_get_drug_description_by_chemblId",
                "args": {"chemblId": "CHEMBL25"},
                "description": "原始问题查询"
            },
            {
                "name": "PubChem_get_CID_by_compound_name",
                "args": {"name": "Aspirin"},
                "description": "原始问题查询"
            }
        ]
        
        # 尝试多次调用，模拟网络不稳定
        for attempt in range(3):
            self.log(f"\n网络模拟尝试 {attempt + 1}/3")
            
            server = StdioServerParameters(
                command="uv",
                args=["run", "tooluniverse-smcp-stdio", "--no-search"]
            )
            
            try:
                async with stdio_client(server) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        
                        for query in problematic_queries:
                            self.log(f"测试: {query['name']}")
                            
                            try:
                                start_time = time.time()
                                
                                # 使用很短的超时来强制触发问题
                                result = await asyncio.wait_for(
                                    session.call_tool(query["name"], query["args"]),
                                    timeout=2.0  # 2秒超时
                                )
                                
                                execution_time = time.time() - start_time
                                self.log(f"✅ 调用成功，耗时 {execution_time:.2f}秒")
                                
                            except asyncio.TimeoutError:
                                execution_time = time.time() - start_time
                                self.log(f"⏰ 调用超时（2秒），实际耗时 {execution_time:.2f}秒")
                                
                            except Exception as e:
                                execution_time = time.time() - start_time
                                error_msg = str(e)
                                
                                self.log(f"❌ 调用失败，耗时 {execution_time:.2f}秒")
                                self.log(f"错误: {error_msg}")
                                
                                if "Transport closed" in error_msg:
                                    self.log("🚨 重现了 Transport closed 错误！", "ERROR")
                                    return True
                                    
            except Exception as e:
                self.log(f"❌ 网络模拟异常: {e}", "ERROR")
                if "Transport closed" in str(e):
                    self.log("🚨 重现了 Transport closed 错误！", "ERROR")
                    return True
                    
        return False
    
    async def test_interrupt_scenarios(self):
        """测试中断场景"""
        self.log("\n" + "=" * 60)
        self.log("测试中断场景")
        self.log("=" * 60)
        
        server = StdioServerParameters(
            command="uv",
            args=["run", "tooluniverse-smcp-stdio", "--no-search"]
        )
        
        try:
            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # 启动一个长时间运行的任务
                    task = asyncio.create_task(
                        session.call_tool("OpenTargets_get_drug_description_by_chemblId", 
                                        {"chemblId": "CHEMBL25"})
                    )
                    
                    # 等待一小段时间后取消任务
                    await asyncio.sleep(0.1)
                    task.cancel()
                    
                    try:
                        result = await task
                        self.log("✅ 任务完成")
                    except asyncio.CancelledError:
                        self.log("⚠️ 任务被取消")
                    except Exception as e:
                        error_msg = str(e)
                        self.log(f"❌ 任务异常: {error_msg}")
                        
                        if "Transport closed" in error_msg:
                            self.log("🚨 重现了 Transport closed 错误！", "ERROR")
                            return True
                            
        except Exception as e:
            self.log(f"❌ 中断测试异常: {e}", "ERROR")
            if "Transport closed" in str(e):
                self.log("🚨 重现了 Transport closed 错误！", "ERROR")
                return True
                
        return False


async def main():
    """主函数"""
    print("开始强制重现 Transport Closed 错误测试")
    print("=" * 80)
    
    reproducer = TransportClosedReproducer()
    
    try:
        # 测试 1: 慢查询
        if await reproducer.test_slow_queries():
            print("\n🎯 通过慢查询测试重现了 Transport closed 错误！")
            return
            
        # 测试 2: 并发调用
        if await reproducer.test_concurrent_calls():
            print("\n🎯 通过并发调用测试重现了 Transport closed 错误！")
            return
            
        # 测试 3: 资源压力
        if await reproducer.test_resource_stress():
            print("\n🎯 通过资源压力测试重现了 Transport closed 错误！")
            return
            
        # 测试 4: 网络模拟
        if await reproducer.test_network_simulation():
            print("\n🎯 通过网络模拟测试重现了 Transport closed 错误！")
            return
            
        # 测试 5: 中断场景
        if await reproducer.test_interrupt_scenarios():
            print("\n🎯 通过中断场景测试重现了 Transport closed 错误！")
            return
            
        print("\n❌ 未能重现 Transport closed 错误")
        print("可能的原因:")
        print("1. 您的环境与我的测试环境不同")
        print("2. 问题可能出现在特定的网络条件下")
        print("3. 问题可能与特定的 MCP 客户端版本有关")
        print("4. 问题可能是间歇性的")
        
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        print(traceback.format_exc())
    
    print("\n✨ 测试完成")


if __name__ == "__main__":
    asyncio.run(main())
