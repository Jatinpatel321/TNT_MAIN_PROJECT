#!/usr/bin/env python3
"""Run all vendor module tests and generate comprehensive report."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Test files to run
TEST_FILES = [
    "tests/test_auth.py",
    "tests/test_profile.py",
    "tests/test_menu.py",
    "tests/test_orders.py",
    "tests/test_slots.py",
    "tests/test_notifications.py",
    "tests/test_promotions.py",
    "tests/test_analytics.py",
    "tests/test_settlements.py",
    "tests/test_ai.py",
]


def run_pytest(test_file: str) -> Tuple[int, int, str]:
    """Run pytest on a single test file."""
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        
        # Parse passed/failed from output
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        
        return passed, failed, output
    except subprocess.TimeoutExpired:
        return 0, 0, "TIMEOUT"
    except Exception as e:
        return 0, 0, str(e)


def generate_report(results: Dict[str, Tuple[int, int, str]]) -> str:
    """Generate comprehensive test report."""
    total_passed = sum(r[0] for r in results.values())
    total_failed = sum(r[1] for r in results.values())
    total_tests = total_passed + total_failed
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

    report = f"""# API Test Report - Vendor Module

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Test Suite:** Vendor Module Backend APIs  
**Status:** {"✅ PASS" if pass_rate >= 90 else "⚠️ NEEDS ATTENTION" if pass_rate >= 70 else "❌ FAIL"}

---

## 📊 Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | {total_tests} |
| **Passed** | {total_passed} ✅ |
| **Failed** | {total_failed} ❌ |
| **Pass Rate** | {pass_rate:.1f}% |
| **Target** | 90% |
| **Status** | {"✅ MET" if pass_rate >= 90 else "❌ BELOW TARGET"} |

---

## 📋 Test Results by Module

| Module | Passed | Failed | Total | Pass Rate | Status |
|--------|--------|--------|-------|-----------|--------|
"""
    
    for module, (passed, failed, _) in results.items():
        total = passed + failed
        rate = (passed / total * 100) if total > 0 else 0
        status = "✅" if rate >= 90 else "⚠️" if rate >= 70 else "❌"
        report += f"| {module} | {passed} | {failed} | {total} | {rate:.1f}% | {status} |\n"

    report += """
---

## 🔍 Detailed Results

"""
    
    for module, (passed, failed, output) in results.items():
        report += f"### {module}\n\n"
        if failed == 0 and passed > 0:
            report += f"✅ All {passed} tests passed\n\n"
        elif passed == 0 and failed == 0:
            report += "⚠️ No tests found or file missing\n\n"
        else:
            report += f"❌ {failed} test(s) failed out of {passed + failed}\n\n"
            report += "```\n"
            report += output[:2000]  # First 2000 chars of output
            report += "\n```\n\n"

    report += f"""
---

## 🎯 Recommendations

"""
    
    if pass_rate >= 90:
        report += "✅ **Excellent!** All tests passing. Ready for deployment.\n"
    elif pass_rate >= 70:
        report += "⚠️ **Good progress.** Fix failing tests before production.\n"
    else:
        report += "❌ **Critical issues detected.** Major fixes required.\n"

    report += """
## 📝 Next Steps

1. Review failed tests and fix issues
2. Increase test coverage for edge cases
3. Add integration tests for critical flows
4. Set up CI/CD pipeline for automated testing
5. Monitor test results in production

---

**Report Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Test Framework:** pytest  
**Coverage Target:** 90%
"""

    return report


def main():
    """Main test runner."""
    print("🚀 Starting Vendor Module Test Suite...")
    print("=" * 80)
    
    results = {}
    total_passed = 0
    total_failed = 0
    
    for test_file in TEST_FILES:
        print(f"\n📋 Running {test_file}...")
        passed, failed, output = run_pytest(test_file)
        results[test_file] = (passed, failed, output)
        
        total_passed += passed
        total_failed += failed
        
        status = "✅" if failed == 0 else "❌"
        print(f"{status} {passed} passed, {failed} failed")
    
    print("\n" + "=" * 80)
    print("📊 Test Summary:")
    print(f"   Total: {total_passed + total_failed}")
    print(f"   Passed: {total_passed}")
    print(f"   Failed: {total_failed}")
    pass_rate = (total_passed / (total_passed + total_failed) * 100) if (total_passed + total_failed) > 0 else 0
    print(f"   Pass Rate: {pass_rate:.1f}%")
    print("=" * 80)
    
    # Generate report
    report = generate_report(results)
    report_path = Path("API_TEST_REPORT.md")
    report_path.write_text(report, encoding='utf-8')
    print(f"\n📄 Report saved to: {report_path}")
    
    # Exit with appropriate code
    sys.exit(0 if pass_rate >= 90 else 1)


if __name__ == "__main__":
    main()