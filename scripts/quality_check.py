#!/usr/bin/env python3
"""
Quality check script for AWS SSM Calendar ICS Generator.
Runs comprehensive code quality checks and generates reports.
"""

import subprocess
import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse


class QualityChecker:
    """Comprehensive code quality checker."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / "src"
        self.tests_dir = project_root / "tests"
        self.results = {}
        
    def run_command(self, command: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
        """Run a command and return exit code, stdout, stderr."""
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=capture_output,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except Exception as e:
            return 1, "", str(e)
    
    def check_black_formatting(self) -> Dict:
        """Check code formatting with Black."""
        print("🔍 Checking Black formatting...")
        
        exit_code, stdout, stderr = self.run_command([
            "black", "--check", "--diff", "src/", "tests/"
        ])
        
        result = {
            "name": "Black Formatting",
            "passed": exit_code == 0,
            "exit_code": exit_code,
            "output": stdout,
            "errors": stderr
        }
        
        if result["passed"]:
            print("✅ Black formatting check passed")
        else:
            print("❌ Black formatting check failed")
            print(f"   Output: {stdout[:200]}...")
        
        return result
    
    def check_isort_imports(self) -> Dict:
        """Check import sorting with isort."""
        print("🔍 Checking import sorting...")
        
        exit_code, stdout, stderr = self.run_command([
            "isort", "--check-only", "--diff", "src/", "tests/"
        ])
        
        result = {
            "name": "Import Sorting (isort)",
            "passed": exit_code == 0,
            "exit_code": exit_code,
            "output": stdout,
            "errors": stderr
        }
        
        if result["passed"]:
            print("✅ Import sorting check passed")
        else:
            print("❌ Import sorting check failed")
        
        return result
    
    def check_flake8_linting(self) -> Dict:
        """Check code linting with Flake8."""
        print("🔍 Running Flake8 linting...")
        
        exit_code, stdout, stderr = self.run_command([
            "flake8", "src/", "tests/", "--statistics"
        ])
        
        result = {
            "name": "Flake8 Linting",
            "passed": exit_code == 0,
            "exit_code": exit_code,
            "output": stdout,
            "errors": stderr
        }
        
        if result["passed"]:
            print("✅ Flake8 linting passed")
        else:
            print("❌ Flake8 linting failed")
            print(f"   Issues found: {len(stdout.splitlines())}")
        
        return result
    
    def check_mypy_types(self) -> Dict:
        """Check type annotations with MyPy."""
        print("🔍 Running MyPy type checking...")
        
        exit_code, stdout, stderr = self.run_command([
            "mypy", "src/", "--ignore-missing-imports"
        ])
        
        result = {
            "name": "MyPy Type Checking",
            "passed": exit_code == 0,
            "exit_code": exit_code,
            "output": stdout,
            "errors": stderr
        }
        
        if result["passed"]:
            print("✅ MyPy type checking passed")
        else:
            print("❌ MyPy type checking failed")
            print(f"   Type errors found: {len(stdout.splitlines())}")
        
        return result
    
    def check_bandit_security(self) -> Dict:
        """Check security issues with Bandit."""
        print("🔍 Running Bandit security check...")
        
        exit_code, stdout, stderr = self.run_command([
            "bandit", "-r", "src/", "-f", "json", "-c", ".bandit"
        ])
        
        # Parse Bandit JSON output
        issues_count = 0
        severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        
        if stdout:
            try:
                bandit_data = json.loads(stdout)
                issues_count = len(bandit_data.get("results", []))
                for issue in bandit_data.get("results", []):
                    severity = issue.get("issue_severity", "UNKNOWN")
                    if severity in severity_counts:
                        severity_counts[severity] += 1
            except json.JSONDecodeError:
                pass
        
        result = {
            "name": "Bandit Security Check",
            "passed": exit_code == 0,
            "exit_code": exit_code,
            "output": stdout,
            "errors": stderr,
            "issues_count": issues_count,
            "severity_counts": severity_counts
        }
        
        if result["passed"]:
            print("✅ Bandit security check passed")
        else:
            print("❌ Bandit security check failed")
            print(f"   Security issues found: {issues_count}")
            for severity, count in severity_counts.items():
                if count > 0:
                    print(f"   {severity}: {count}")
        
        return result
    
    def check_safety_dependencies(self) -> Dict:
        """Check dependency vulnerabilities with Safety."""
        print("🔍 Running Safety dependency check...")
        
        exit_code, stdout, stderr = self.run_command([
            "safety", "check", "--json"
        ])
        
        # Parse Safety JSON output
        vulnerabilities_count = 0
        if stdout and exit_code != 0:
            try:
                safety_data = json.loads(stdout)
                vulnerabilities_count = len(safety_data)
            except json.JSONDecodeError:
                pass
        
        result = {
            "name": "Safety Dependency Check",
            "passed": exit_code == 0,
            "exit_code": exit_code,
            "output": stdout,
            "errors": stderr,
            "vulnerabilities_count": vulnerabilities_count
        }
        
        if result["passed"]:
            print("✅ Safety dependency check passed")
        else:
            print("❌ Safety dependency check failed")
            print(f"   Vulnerabilities found: {vulnerabilities_count}")
        
        return result
    
    def run_tests_with_coverage(self) -> Dict:
        """Run tests with coverage measurement."""
        print("🔍 Running tests with coverage...")
        
        exit_code, stdout, stderr = self.run_command([
            "pytest", "tests/", "--cov=src", "--cov-report=term-missing", 
            "--cov-report=json", "-v"
        ])
        
        # Parse coverage data
        coverage_percentage = 0
        coverage_file = self.project_root / "coverage.json"
        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    coverage_percentage = coverage_data.get("totals", {}).get("percent_covered", 0)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        result = {
            "name": "Test Coverage",
            "passed": exit_code == 0 and coverage_percentage >= 80,
            "exit_code": exit_code,
            "output": stdout,
            "errors": stderr,
            "coverage_percentage": coverage_percentage
        }
        
        if result["passed"]:
            print(f"✅ Tests passed with {coverage_percentage:.1f}% coverage")
        else:
            print(f"❌ Tests failed or coverage below 80% (current: {coverage_percentage:.1f}%)")
        
        return result
    
    def generate_report(self) -> Dict:
        """Generate comprehensive quality report."""
        print("\n" + "="*60)
        print("🚀 AWS SSM Calendar ICS Generator - Quality Check Report")
        print("="*60)
        
        # Run all checks
        checks = [
            self.check_black_formatting(),
            self.check_isort_imports(),
            self.check_flake8_linting(),
            self.check_mypy_types(),
            self.check_bandit_security(),
            self.check_safety_dependencies(),
            self.run_tests_with_coverage(),
        ]
        
        # Calculate overall results
        passed_checks = sum(1 for check in checks if check["passed"])
        total_checks = len(checks)
        overall_passed = passed_checks == total_checks
        
        report = {
            "timestamp": subprocess.check_output(["date", "-Iseconds"]).decode().strip(),
            "overall_passed": overall_passed,
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "checks": checks
        }
        
        # Print summary
        print(f"\n📊 Quality Check Summary:")
        print(f"   Passed: {passed_checks}/{total_checks}")
        print(f"   Success Rate: {(passed_checks/total_checks)*100:.1f}%")
        
        if overall_passed:
            print("\n🎉 All quality checks passed! Code is ready for production.")
        else:
            print("\n⚠️  Some quality checks failed. Please review and fix issues.")
        
        # Print detailed results
        print(f"\n📋 Detailed Results:")
        for check in checks:
            status = "✅ PASS" if check["passed"] else "❌ FAIL"
            print(f"   {status} {check['name']}")
        
        return report
    
    def save_report(self, report: Dict, output_file: Optional[Path] = None):
        """Save quality report to JSON file."""
        if output_file is None:
            output_file = self.project_root / "quality_report.json"
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Quality report saved to: {output_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run comprehensive quality checks")
    parser.add_argument(
        "--output", "-o", 
        type=Path, 
        help="Output file for quality report (default: quality_report.json)"
    )
    parser.add_argument(
        "--fail-fast", 
        action="store_true", 
        help="Stop on first failure"
    )
    
    args = parser.parse_args()
    
    # Find project root
    project_root = Path(__file__).parent.parent
    
    # Run quality checks
    checker = QualityChecker(project_root)
    report = checker.generate_report()
    
    # Save report
    checker.save_report(report, args.output)
    
    # Exit with appropriate code
    if not report["overall_passed"]:
        print(f"\n❌ Quality checks failed. Exit code: 1")
        sys.exit(1)
    else:
        print(f"\n✅ All quality checks passed. Exit code: 0")
        sys.exit(0)


if __name__ == "__main__":
    main()