#!/usr/bin/env python3
"""Microbenchmark request-scoped credential instance reuse.

This benchmark is intentionally network-free: it isolates the framework overhead and the cost of
constructing an authenticated SDK-style tool. Run from the repository root with::

    python scripts/benchmark_request_credentials.py --iterations 1000
"""

from __future__ import annotations

import argparse
import os
import time

from tooluniverse import ToolUniverse
from tooluniverse.base_tool import BaseTool


os.environ.setdefault("TOOLUNIVERSE_CACHE_PERSIST", "false")


class BenchmarkCredentialTool(BaseTool):
    instances = 0

    def __init__(self, tool_config):
        super().__init__(tool_config)
        type(self).instances += 1
        # Approximate a modest authenticated SDK/session initialization cost.
        time.sleep(0.001)
        self.api_key = self.credential("BENCHMARK_API_KEY")

    def run(self, arguments=None, **kwargs):
        return self.api_key is not None


CONFIG = {
    "name": "BenchmarkCredentialTool",
    "type": "BenchmarkCredentialTool",
    "description": "Benchmark request-scoped instance reuse",
    "parameter": {"type": "object", "properties": {}},
}


def run_case(iterations: int, cache_size: int) -> tuple[float, int]:
    BenchmarkCredentialTool.instances = 0
    tool_universe = ToolUniverse(
        tool_files={},
        keep_default_tools=False,
        credential_instance_cache_size=cache_size,
        credential_instance_cache_ttl=900,
    )
    tool_universe.register_custom_tool(BenchmarkCredentialTool, tool_config=CONFIG)
    call = {"name": "BenchmarkCredentialTool", "arguments": {}}

    started = time.perf_counter()
    for _ in range(iterations):
        result = tool_universe.run_one_function(
            call.copy(),
            validate=False,
            credentials={"BENCHMARK_API_KEY": "benchmark-tenant"},
        )
        if result is not True:
            raise RuntimeError(f"unexpected benchmark result: {result!r}")
    elapsed = time.perf_counter() - started
    return elapsed, BenchmarkCredentialTool.instances


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1000)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be positive")

    uncached_seconds, uncached_instances = run_case(args.iterations, cache_size=0)
    cached_seconds, cached_instances = run_case(args.iterations, cache_size=256)
    speedup = uncached_seconds / cached_seconds

    print(f"iterations: {args.iterations}")
    print(
        f"uncached: {uncached_seconds:.4f}s, instances={uncached_instances}, "
        f"{args.iterations / uncached_seconds:.1f} calls/s"
    )
    print(
        f"cached:   {cached_seconds:.4f}s, instances={cached_instances}, "
        f"{args.iterations / cached_seconds:.1f} calls/s"
    )
    print(f"framework microbenchmark speedup: {speedup:.2f}x")


if __name__ == "__main__":
    main()
