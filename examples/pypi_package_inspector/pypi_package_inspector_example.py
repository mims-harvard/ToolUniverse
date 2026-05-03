"""
PyPI Package Inspector Example

This example demonstrates how to use the PyPIPackageInspector tool to evaluate
Python packages for quality metrics including popularity, maintenance,
documentation, compatibility, and security.
"""

from tooluniverse import ToolUniverse


def inspect_single_package():
    """Inspect a single package and display detailed metrics"""
    print("=" * 70)
    print("Example 1: Inspect a single package (requests)")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "PyPIPackageInspector",
        "arguments": {
            "package_name": "requests",
            "include_github": True,
            "include_downloads": True
        }
    })
    
    if result.get('status') == 'success':
        print(f"\n✅ Package: {result['package_name']}")
        print(f"   Recommendation: {result['recommendation']}")
        
        scores = result['quality_scores']
        print(f"\n📊 Quality Scores:")
        print(f"   Overall:        {scores['overall_score']}/100")
        print(f"   Popularity:     {scores['popularity_score']}/100")
        print(f"   Maintenance:    {scores['maintenance_score']}/100")
        print(f"   Documentation:  {scores['documentation_score']}/100")
        print(f"   Compatibility:  {scores['compatibility_score']}/100")
        print(f"   Security:       {scores['security_score']}/100")
        
        # Show key metrics
        pypi = result['pypi_metadata']
        downloads = result['download_stats']
        github = result['github_stats']
        
        print(f"\n📦 PyPI Info:")
        print(f"   Version: {pypi.get('version')}")
        print(f"   License: {pypi.get('license')}")
        print(f"   Last Release: {pypi.get('days_since_last_release')} days ago")
        print(f"   Total Releases: {pypi.get('total_releases')}")
        
        print(f"\n📊 Downloads:")
        print(f"   Last Month: {downloads.get('downloads_last_month'):,}")
        
        print(f"\n🐙 GitHub:")
        print(f"   Stars: {github.get('stars'):,}")
        print(f"   Forks: {github.get('forks'):,}")
        print(f"   Open Issues: {github.get('open_issues')}")
    else:
        print(f"❌ Error: {result.get('error')}")


def compare_packages():
    """Compare multiple packages for quality"""
    print("\n" + "=" * 70)
    print("Example 2: Compare multiple HTTP client packages")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    packages = ["requests", "httpx", "aiohttp"]
    results = []
    
    for pkg in packages:
        result = tu.run({
            "name": "PyPIPackageInspector",
            "arguments": {
                "package_name": pkg,
                "include_github": True,
                "include_downloads": True
            }
        })
        
        if result.get('status') == 'success':
            results.append({
                'name': pkg,
                'overall': result['quality_scores']['overall_score'],
                'popularity': result['quality_scores']['popularity_score'],
                'maintenance': result['quality_scores']['maintenance_score'],
                'downloads': result['download_stats'].get('downloads_last_month', 0)
            })
    
    # Sort by overall score
    results.sort(key=lambda x: x['overall'], reverse=True)
    
    print(f"\n📊 Package Comparison:")
    print(f"{'Rank':<6} {'Package':<12} {'Overall':<10} {'Popularity':<12} "
          f"{'Maintenance':<13} {'Downloads/Month':<15}")
    print("-" * 70)
    
    for i, pkg in enumerate(results, 1):
        print(f"{i:<6} {pkg['name']:<12} {pkg['overall']:<10} "
              f"{pkg['popularity']:<12} {pkg['maintenance']:<13} "
              f"{pkg['downloads']:>14,}")


def quick_evaluation():
    """Quick evaluation without external APIs (faster)"""
    print("\n" + "=" * 70)
    print("Example 3: Quick evaluation (PyPI metadata only)")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "PyPIPackageInspector",
        "arguments": {
            "package_name": "pandas",
            "include_github": False,  # Skip GitHub API
            "include_downloads": False  # Skip pypistats API
        }
    })
    
    if result.get('status') == 'success':
        print(f"\n✅ Package: {result['package_name']}")
        print(f"   Overall Score: {result['quality_scores']['overall_score']}/100")
        print(f"   (Note: Scores based on PyPI metadata only)")
        
        pypi = result['pypi_metadata']
        print(f"\n📦 Basic Info:")
        print(f"   Version: {pypi.get('version')}")
        print(f"   Summary: {pypi.get('summary')[:80]}...")
        print(f"   Python: {pypi.get('requires_python', 'Not specified')}")
    else:
        print(f"❌ Error: {result.get('error')}")


def evaluate_for_dependency():
    """Practical use case: Evaluate before adding as dependency"""
    print("\n" + "=" * 70)
    print("Example 4: Evaluate package before adding as dependency")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    package_to_evaluate = "typer"
    
    print(f"\n🔍 Evaluating '{package_to_evaluate}' for use in project...")
    
    result = tu.run({
        "name": "PyPIPackageInspector",
        "arguments": {
            "package_name": package_to_evaluate
        }
    })
    
    if result.get('status') == 'success':
        scores = result['quality_scores']
        overall = scores['overall_score']
        
        print(f"\n📊 Evaluation Results:")
        print(f"   Overall Quality: {overall}/100")
        print(f"   {result['recommendation']}")
        
        # Decision logic
        if overall >= 80:
            decision = "✅ RECOMMENDED - High quality, safe to use"
        elif overall >= 60:
            decision = "👍 ACCEPTABLE - Good quality, proceed with caution"
        elif overall >= 40:
            decision = "⚠️  REVIEW NEEDED - Check alternatives"
        else:
            decision = "❌ NOT RECOMMENDED - Find better alternative"
        
        print(f"\n🎯 Decision: {decision}")
        
        # Show concerns if any
        concerns = []
        if scores['maintenance_score'] < 50:
            concerns.append("⚠️  Low maintenance activity")
        if scores['popularity_score'] < 30:
            concerns.append("⚠️  Limited adoption")
        if scores['documentation_score'] < 40:
            concerns.append("⚠️  Insufficient documentation")
        
        if concerns:
            print(f"\n⚠️  Concerns:")
            for concern in concerns:
                print(f"   {concern}")
        
        # Show strengths
        strengths = []
        if scores['security_score'] >= 70:
            strengths.append("✅ Good security practices")
        if scores['compatibility_score'] >= 70:
            strengths.append("✅ Wide compatibility")
        if scores['maintenance_score'] >= 70:
            strengths.append("✅ Actively maintained")
        
        if strengths:
            print(f"\n✅ Strengths:")
            for strength in strengths:
                print(f"   {strength}")
    else:
        print(f"❌ Error: {result.get('error')}")


def main():
    """Run all examples"""
    print("\n🔬 PyPI Package Inspector Examples\n")
    
    # Run examples
    inspect_single_package()
    compare_packages()
    quick_evaluation()
    evaluate_for_dependency()
    
    print("\n" + "=" * 70)
    print("✅ All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()

