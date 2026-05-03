#!/usr/bin/env python3
"""
Debug Transport Closed Error - 诊断脚本

这个脚本用于重现和诊断 tooluniverse-smcp-stdio 中的 "Transport closed" 错误。
包含三种测试模式来定位问题根源。

使用方法:
    python debug_transport_closed.py [--mode MODE] [--verbose]
    
模式:
    direct  - 直接测试（绕过 MCP）
    stdio   - stdio MCP 测试（重现问题）
    http    - HTTP MCP 测试（对照组）
    all     - 运行所有模式（默认）
"""

import asyncio
import json
import subprocess
import sys
import time
import traceback
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
import threading
import queue

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamablehttp_client
except ImportError:
    print("❌ MCP 库未安装: pip install mcp")
    sys.exit(1)

try:
    from tooluniverse import ToolUniverse
except ImportError:
    print("❌ ToolUniverse 未安装或路径错误")
    sys.exit(1)


class TransportClosedDebugger:
    """Transport Closed 错误诊断器"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = []
        
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def log_verbose(self, message: str):
        """详细日志"""
        if self.verbose:
            self.log(message, "DEBUG")
            
    def test_tools_direct(self) -> Dict[str, Any]:
        """模式 A: 直接测试（绕过 MCP）"""
        self.log("=" * 60)
        self.log("模式 A: 直接测试（绕过 MCP）")
        self.log("=" * 60)
        
        results = {
            "mode": "direct",
            "tests": [],
            "summary": {"success": 0, "failed": 0, "timeout": 0}
        }
        
        # 初始化 ToolUniverse
        try:
            self.log("初始化 ToolUniverse...")
            tooluni = ToolUniverse()
            tooluni.load_tools()
            self.log(f"✅ ToolUniverse 初始化成功，加载了 {len(tooluni.all_tool_dict)} 个工具")
        except Exception as e:
            self.log(f"❌ ToolUniverse 初始化失败: {e}", "ERROR")
            return results
            
        # 测试用例
        test_cases = [
            {
                "name": "OpenTargets_get_drug_description_by_chemblId",
                "args": {"chemblId": "CHEMBL25"},
                "description": "OpenTargets GraphQL 查询（无 timeout）"
            },
            {
                "name": "PubChem_get_CID_by_compound_name", 
                "args": {"name": "Aspirin"},
                "description": "PubChem REST API 查询（30s timeout）"
            },
            {
                "name": "UniProt_search",
                "args": {"query": "gene:MEIOB", "limit": 5},
                "description": "UniProt 搜索（对照组，已知快速）"
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            self.log(f"\n[测试 {i+1}/{len(test_cases)}] {test_case['name']}")
            self.log(f"描述: {test_case['description']}")
            self.log(f"参数: {test_case['args']}")
            
            test_result = {
                "name": test_case["name"],
                "args": test_case["args"],
                "description": test_case["description"],
                "success": False,
                "execution_time": 0,
                "error": None,
                "result_size": 0,
                "timeout": False
            }
            
            try:
                start_time = time.time()
                
                # 使用线程超时来防止挂起
                result_container = [None]
                exception_container = [None]
                
                def run_tool():
                    try:
                        result_container[0] = tooluni.run_one_function({
                            "name": test_case["name"],
                            "arguments": test_case["args"]
                        })
                    except Exception as e:
                        exception_container[0] = e
                
                thread = threading.Thread(target=run_tool)
                thread.daemon = True
                thread.start()
                
                # 等待最多 60 秒
                thread.join(timeout=60)
                
                execution_time = time.time() - start_time
                test_result["execution_time"] = execution_time
                
                if thread.is_alive():
                    self.log(f"⏰ 工具执行超时（60秒）", "WARNING")
                    test_result["timeout"] = True
                    results["summary"]["timeout"] += 1
                elif exception_container[0]:
                    error = exception_container[0]
                    self.log(f"❌ 工具执行失败: {error}", "ERROR")
                    test_result["error"] = str(error)
                    results["summary"]["failed"] += 1
                else:
                    result = result_container[0]
                    if isinstance(result, dict) and "error" in result:
                        self.log(f"⚠️ 工具返回错误: {result['error']}", "WARNING")
                        test_result["error"] = result["error"]
                        results["summary"]["failed"] += 1
                    else:
                        self.log(f"✅ 工具执行成功，耗时 {execution_time:.2f}秒")
                        test_result["success"] = True
                        test_result["result_size"] = len(str(result))
                        results["summary"]["success"] += 1
                        
                        if self.verbose:
                            self.log(f"结果大小: {test_result['result_size']} 字符")
                            if isinstance(result, dict) and len(str(result)) < 1000:
                                self.log(f"结果预览: {json.dumps(result, indent=2)[:500]}...")
                
            except Exception as e:
                self.log(f"❌ 测试异常: {e}", "ERROR")
                test_result["error"] = str(e)
                test_result["execution_time"] = time.time() - start_time
                results["summary"]["failed"] += 1
                
                if self.verbose:
                    self.log(traceback.format_exc(), "DEBUG")
            
            results["tests"].append(test_result)
            
        return results
    
    async def test_tools_stdio(self) -> Dict[str, Any]:
        """模式 B: stdio MCP 测试（重现问题）"""
        self.log("\n" + "=" * 60)
        self.log("模式 B: stdio MCP 测试（重现问题）")
        self.log("=" * 60)
        
        results = {
            "mode": "stdio",
            "tests": [],
            "summary": {"success": 0, "failed": 0, "transport_closed": 0}
        }
        
        # 测试用例
        test_cases = [
            {
                "name": "OpenTargets_get_drug_description_by_chemblId",
                "args": {"chemblId": "CHEMBL25"},
                "description": "OpenTargets GraphQL 查询"
            },
            {
                "name": "PubChem_get_CID_by_compound_name",
                "args": {"name": "Aspirin"},
                "description": "PubChem REST API 查询"
            },
            {
                "name": "UniProt_search",
                "args": {"query": "gene:MEIOB", "limit": 5},
                "description": "UniProt 搜索（对照组）"
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            self.log(f"\n[测试 {i+1}/{len(test_cases)}] {test_case['name']}")
            self.log(f"描述: {test_case['description']}")
            
            test_result = {
                "name": test_case["name"],
                "args": test_case["args"],
                "description": test_case["description"],
                "success": False,
                "execution_time": 0,
                "error": None,
                "transport_closed": False,
                "server_logs": []
            }
            
            try:
                # 启动 stdio 服务器
                server = StdioServerParameters(
                    command="uv",
                    args=["run", "tooluniverse-smcp-stdio", "--no-search"]
                )
                
                start_time = time.time()
                
                async with stdio_client(server) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        
                        # 调用工具
                        try:
                            result = await session.call_tool(test_case["name"], test_case["args"])
                            execution_time = time.time() - start_time
                            test_result["execution_time"] = execution_time
                            
                            self.log(f"✅ stdio 调用成功，耗时 {execution_time:.2f}秒")
                            test_result["success"] = True
                            results["summary"]["success"] += 1
                            
                            if self.verbose:
                                content_text = ""
                                for content in result.content:
                                    content_text += content.text
                                test_result["result_size"] = len(content_text)
                                self.log(f"结果大小: {test_result['result_size']} 字符")
                                
                        except Exception as e:
                            execution_time = time.time() - start_time
                            test_result["execution_time"] = execution_time
                            error_msg = str(e)
                            
                            if "Transport closed" in error_msg:
                                self.log(f"🚨 重现了 Transport closed 错误！", "ERROR")
                                test_result["transport_closed"] = True
                                results["summary"]["transport_closed"] += 1
                            else:
                                self.log(f"❌ stdio 调用失败: {error_msg}", "ERROR")
                                test_result["error"] = error_msg
                                results["summary"]["failed"] += 1
                                
                            if self.verbose:
                                self.log(traceback.format_exc(), "DEBUG")
                                
            except Exception as e:
                execution_time = time.time() - start_time
                test_result["execution_time"] = execution_time
                error_msg = str(e)
                
                if "Transport closed" in error_msg:
                    self.log(f"🚨 重现了 Transport closed 错误！", "ERROR")
                    test_result["transport_closed"] = True
                    results["summary"]["transport_closed"] += 1
                else:
                    self.log(f"❌ stdio 测试异常: {error_msg}", "ERROR")
                    test_result["error"] = error_msg
                    results["summary"]["failed"] += 1
                    
                if self.verbose:
                    self.log(traceback.format_exc(), "DEBUG")
            
            results["tests"].append(test_result)
            
        return results
    
    async def test_tools_http(self) -> Dict[str, Any]:
        """模式 C: HTTP MCP 测试（对照组）"""
        self.log("\n" + "=" * 60)
        self.log("模式 C: HTTP MCP 测试（对照组）")
        self.log("=" * 60)
        
        results = {
            "mode": "http",
            "tests": [],
            "summary": {"success": 0, "failed": 0, "server_startup_failed": False}
        }
        
        # 启动 HTTP 服务器
        self.log("启动 HTTP MCP 服务器...")
        server_process = None
        
        try:
            server_process = subprocess.Popen([
                "uv", "run", "tooluniverse-smcp", 
                "--transport", "http",
                "--port", "7001",
                "--no-search"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # 等待服务器启动
            await asyncio.sleep(5)
            
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                self.log(f"❌ 服务器启动失败: {stderr}", "ERROR")
                results["summary"]["server_startup_failed"] = True
                return results
                
            self.log("✅ HTTP 服务器启动成功")
            
        except Exception as e:
            self.log(f"❌ 无法启动 HTTP 服务器: {e}", "ERROR")
            results["summary"]["server_startup_failed"] = True
            return results
        
        # 测试用例
        test_cases = [
            {
                "name": "OpenTargets_get_drug_description_by_chemblId",
                "args": {"chemblId": "CHEMBL25"},
                "description": "OpenTargets GraphQL 查询"
            },
            {
                "name": "PubChem_get_CID_by_compound_name",
                "args": {"name": "Aspirin"},
                "description": "PubChem REST API 查询"
            },
            {
                "name": "UniProt_search",
                "args": {"query": "gene:MEIOB", "limit": 5},
                "description": "UniProt 搜索（对照组）"
            }
        ]
        
        try:
            async with streamablehttp_client("http://localhost:7001") as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    for i, test_case in enumerate(test_cases):
                        self.log(f"\n[测试 {i+1}/{len(test_cases)}] {test_case['name']}")
                        self.log(f"描述: {test_case['description']}")
                        
                        test_result = {
                            "name": test_case["name"],
                            "args": test_case["args"],
                            "description": test_case["description"],
                            "success": False,
                            "execution_time": 0,
                            "error": None
                        }
                        
                        try:
                            start_time = time.time()
                            result = await session.call_tool(test_case["name"], test_case["args"])
                            execution_time = time.time() - start_time
                            test_result["execution_time"] = execution_time
                            
                            self.log(f"✅ HTTP 调用成功，耗时 {execution_time:.2f}秒")
                            test_result["success"] = True
                            results["summary"]["success"] += 1
                            
                            if self.verbose:
                                content_text = ""
                                for content in result.content:
                                    content_text += content.text
                                test_result["result_size"] = len(content_text)
                                self.log(f"结果大小: {test_result['result_size']} 字符")
                                
                        except Exception as e:
                            execution_time = time.time() - start_time
                            test_result["execution_time"] = execution_time
                            error_msg = str(e)
                            
                            self.log(f"❌ HTTP 调用失败: {error_msg}", "ERROR")
                            test_result["error"] = error_msg
                            results["summary"]["failed"] += 1
                            
                            if self.verbose:
                                self.log(traceback.format_exc(), "DEBUG")
                        
                        results["tests"].append(test_result)
                        
        except Exception as e:
            self.log(f"❌ HTTP 测试异常: {e}", "ERROR")
            if self.verbose:
                self.log(traceback.format_exc(), "DEBUG")
        
        finally:
            # 清理服务器进程
            if server_process:
                try:
                    server_process.terminate()
                    server_process.wait(timeout=10)
                    self.log("✅ HTTP 服务器已关闭")
                except:
                    server_process.kill()
                    self.log("⚠️ 强制关闭 HTTP 服务器")
        
        return results
    
    def print_summary(self, all_results: List[Dict[str, Any]]):
        """打印测试总结"""
        self.log("\n" + "=" * 80)
        self.log("测试总结")
        self.log("=" * 80)
        
        for result in all_results:
            mode = result["mode"]
            summary = result["summary"]
            
            self.log(f"\n{mode.upper()} 模式:")
            self.log(f"  成功: {summary['success']}")
            self.log(f"  失败: {summary['failed']}")
            
            if "timeout" in summary:
                self.log(f"  超时: {summary['timeout']}")
            if "transport_closed" in summary:
                self.log(f"  Transport closed: {summary['transport_closed']}")
            if "server_startup_failed" in summary:
                self.log(f"  服务器启动失败: {summary['server_startup_failed']}")
        
        # 分析结果
        self.log("\n" + "=" * 80)
        self.log("问题分析")
        self.log("=" * 80)
        
        direct_result = next((r for r in all_results if r["mode"] == "direct"), None)
        stdio_result = next((r for r in all_results if r["mode"] == "stdio"), None)
        http_result = next((r for r in all_results if r["mode"] == "http"), None)
        
        if direct_result and stdio_result:
            self.log("\n🔍 直接测试 vs stdio 测试对比:")
            
            for i, direct_test in enumerate(direct_result["tests"]):
                stdio_test = stdio_result["tests"][i] if i < len(stdio_result["tests"]) else None
                
                if direct_test["name"] == stdio_test["name"]:
                    self.log(f"\n工具: {direct_test['name']}")
                    self.log(f"  直接测试: {direct_test['execution_time']:.2f}s, 成功: {direct_test['success']}")
                    
                    if stdio_test:
                        self.log(f"  stdio测试: {stdio_test['execution_time']:.2f}s, 成功: {stdio_test['success']}")
                        if stdio_test.get("transport_closed"):
                            self.log(f"  🚨 stdio 出现 Transport closed 错误！")
                            
                            # 分析原因
                            if direct_test["timeout"]:
                                self.log(f"  💡 原因分析: 工具本身超时（{direct_test['execution_time']:.2f}s）")
                            elif direct_test["execution_time"] > 30:
                                self.log(f"  💡 原因分析: 工具执行时间过长（{direct_test['execution_time']:.2f}s）")
                            else:
                                self.log(f"  💡 原因分析: stdio 传输层问题")
        
        # 建议修复方案
        self.log("\n" + "=" * 80)
        self.log("建议修复方案")
        self.log("=" * 80)
        
        if stdio_result and stdio_result["summary"]["transport_closed"] > 0:
            self.log("\n🚨 检测到 Transport closed 错误，建议修复方案:")
            
            # 检查 GraphQL 工具超时
            opentargets_test = next((t for t in direct_result["tests"] if "OpenTargets" in t["name"]), None)
            if opentargets_test and opentargets_test["timeout"]:
                self.log("1. GraphQL 工具缺少 timeout 参数")
                self.log("   - 在 src/tooluniverse/graphql_tool.py 的 execute_query() 中添加 timeout=60")
                
            # 检查执行时间
            slow_tools = [t for t in direct_result["tests"] if t["execution_time"] > 30]
            if slow_tools:
                self.log("2. 工具执行时间过长")
                for tool in slow_tools:
                    self.log(f"   - {tool['name']}: {tool['execution_time']:.2f}s")
                self.log("   - 考虑优化查询或增加 MCP 客户端超时")
                
            self.log("3. 添加重试机制")
            self.log("   - 为网络请求添加指数退避重试")
            
        else:
            self.log("\n✅ 未检测到 Transport closed 错误")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Debug Transport Closed Error")
    parser.add_argument("--mode", choices=["direct", "stdio", "http", "all"], 
                       default="all", help="测试模式")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="详细输出")
    
    args = parser.parse_args()
    
    debugger = TransportClosedDebugger(verbose=args.verbose)
    
    debugger.log("开始 Transport Closed 错误诊断")
    debugger.log(f"测试模式: {args.mode}")
    
    all_results = []
    
    try:
        if args.mode in ["direct", "all"]:
            result = debugger.test_tools_direct()
            all_results.append(result)
            
        if args.mode in ["stdio", "all"]:
            result = await debugger.test_tools_stdio()
            all_results.append(result)
            
        if args.mode in ["http", "all"]:
            result = await debugger.test_tools_http()
            all_results.append(result)
            
    except KeyboardInterrupt:
        debugger.log("\n⚠️ 测试被用户中断", "WARNING")
    except Exception as e:
        debugger.log(f"\n❌ 测试异常: {e}", "ERROR")
        if args.verbose:
            debugger.log(traceback.format_exc(), "DEBUG")
    
    # 打印总结
    debugger.print_summary(all_results)
    
    debugger.log("\n✨ 诊断完成")


if __name__ == "__main__":
    asyncio.run(main())
