# PyPI Package Inspector - Quick Start

## 📖 Overview

The PyPI Package Inspector tool provides comprehensive quality evaluation for Python packages by analyzing:

- **Popularity**: Downloads, GitHub stars, forks
- **Maintenance**: Release frequency, recent activity
- **Documentation**: Docs availability, description quality
- **Compatibility**: Wheel support, Python versions
- **Security**: License, active maintenance, issue management

## 🚀 Quick Start

### Basic Usage

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Inspect a package
result = tu.run({
    "name": "PyPIPackageInspector",
    "arguments": {
        "package_name": "requests"
    }
})

# Check the results
if result['status'] == 'success':
    print(f"Overall Score: {result['quality_scores']['overall_score']}/100")
    print(f"Recommendation: {result['recommendation']}")
```

### Run Examples

```bash
# Run all examples
python examples/pypi_package_inspector_example.py

# Or import and run specific examples
from examples.pypi_package_inspector_example import inspect_single_package
inspect_single_package()
```

## 📊 Understanding Scores

Scores are on a 0-100 scale for each dimension:

- **90-100**: Excellent
- **70-89**: Good
- **50-69**: Acceptable
- **30-49**: Poor
- **0-29**: Very Poor

### Overall Score Calculation

```
Overall = Popularity × 0.25
        + Maintenance × 0.30
        + Documentation × 0.20
        + Compatibility × 0.15
        + Security × 0.10
```

## 🎯 Common Use Cases

### 1. Evaluate Before Adding Dependency

```python
result = tu.run({
    "name": "PyPIPackageInspector",
    "arguments": {"package_name": "your-package-name"}
})

overall = result['quality_scores']['overall_score']
if overall >= 80:
    print("✅ Safe to use")
elif overall >= 60:
    print("⚠️  Proceed with caution")
else:
    print("❌ Consider alternatives")
```

### 2. Compare Multiple Packages

```python
packages = ["requests", "httpx", "aiohttp"]

for pkg in packages:
    result = tu.run({
        "name": "PyPIPackageInspector",
        "arguments": {"package_name": pkg}
    })
    
    if result['status'] == 'success':
        score = result['quality_scores']['overall_score']
        print(f"{pkg}: {score}/100")
```

### 3. Quick Check (PyPI only, faster)

```python
result = tu.run({
    "name": "PyPIPackageInspector",
    "arguments": {
        "package_name": "numpy",
        "include_github": False,    # Skip GitHub API
        "include_downloads": False  # Skip pypistats API
    }
})
```

## 🔧 Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `package_name` | string | Yes | - | PyPI package name |
| `include_github` | boolean | No | `true` | Fetch GitHub stats |
| `include_downloads` | boolean | No | `true` | Fetch download stats |

## 📦 Return Value

```python
{
    "status": "success",
    "package_name": "requests",
    "quality_scores": {
        "overall_score": 95,
        "popularity_score": 98,
        "maintenance_score": 92,
        "documentation_score": 95,
        "compatibility_score": 90,
        "security_score": 88
    },
    "recommendation": "✅ HIGHLY RECOMMENDED - ...",
    "pypi_metadata": { ... },
    "download_stats": { ... },
    "github_stats": { ... }
}
```

## ⚡ Performance Tips

1. **Disable External APIs for Speed**:
   ```python
   # Only PyPI (fastest, ~1-2 seconds)
   {
       "package_name": "pkg",
       "include_github": False,
       "include_downloads": False
   }
   ```

2. **Batch Evaluations**: Add small delays between calls to respect rate limits
   ```python
   import time
   for pkg in packages:
       result = inspect(pkg)
       time.sleep(0.5)  # Rate limiting
   ```

3. **Cache Results**: Store inspection results to avoid repeated API calls

## 🐛 Troubleshooting

### Package Not Found
```python
result = tu.run({
    "name": "PyPIPackageInspector",
    "arguments": {"package_name": "invalid-package"}
})
# Returns: {"status": "error", "error": "Package not found on PyPI"}
```

### GitHub URL Not Available
If a package doesn't have a GitHub URL in its metadata, `github_stats` will be empty.

### Rate Limits
- PyPI: No strict limits
- pypistats.org: Be respectful with requests
- GitHub: 60 requests/hour (unauthenticated), 5000/hour (with token)

To add GitHub token:
```python
# In tool_config
tool_config = {"github_token": "your_token_here"}
```

## 📚 More Examples

See `examples/pypi_package_inspector_example.py` for:
- Detailed single package inspection
- Multi-package comparison
- Quick evaluation
- Dependency evaluation workflow

## 🤝 Integration

This tool is automatically used in `tool_discover.py` for package discovery and evaluation. It ranks packages by quality to recommend the best options.

## 📝 Notes

- Scores are calculated based on objective metrics
- No score is perfect - review the detailed metrics for your specific needs
- Maintenance score heavily weighted as unmaintained packages pose risks
- Consider project requirements when interpreting scores

---

For the full example code, see: `examples/pypi_package_inspector_example.py`

For implementation details, see: `PYPI_INSPECTOR_INTEGRATION_SUMMARY.md`

