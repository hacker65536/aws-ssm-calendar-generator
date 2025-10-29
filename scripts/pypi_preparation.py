#!/usr/bin/env python3
"""
PyPI Package Preparation Script

This script prepares the package for PyPI publication (future use).
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional


class PyPIPreparation:
    """Handles PyPI package preparation."""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root or os.getcwd())
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
    
    def clean_build_artifacts(self):
        """Clean previous build artifacts."""
        print("🧹 Cleaning build artifacts...")
        
        # Remove dist directory
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
            print("  ✅ Removed dist/")
        
        # Remove build directory
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
            print("  ✅ Removed build/")
        
        # Remove egg-info directories
        for egg_info in self.project_root.glob("*.egg-info"):
            if egg_info.is_dir():
                shutil.rmtree(egg_info)
                print(f"  ✅ Removed {egg_info.name}")
        
        print("✅ Build artifacts cleaned")
    
    def validate_package_structure(self) -> bool:
        """Validate package structure for PyPI."""
        print("🔍 Validating package structure...")
        
        required_files = [
            "README.md",
            "pyproject.toml",
            "setup.py",
            "src/__init__.py",
            "src/cli.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            print("❌ Missing required files:")
            for file_path in missing_files:
                print(f"  - {file_path}")
            return False
        
        print("✅ Package structure validation passed")
        return True
    
    def validate_metadata(self) -> bool:
        """Validate package metadata."""
        print("🔍 Validating package metadata...")
        
        # Check pyproject.toml
        pyproject_file = self.project_root / "pyproject.toml"
        content = pyproject_file.read_text(encoding='utf-8')
        
        required_fields = [
            'name =',
            'version =',
            'description =',
            'readme =',
            'requires-python =',
            'authors =',
            'dependencies ='
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in content:
                missing_fields.append(field)
        
        if missing_fields:
            print("❌ Missing required metadata fields in pyproject.toml:")
            for field in missing_fields:
                print(f"  - {field}")
            return False
        
        print("✅ Package metadata validation passed")
        return True
    
    def build_package(self) -> bool:
        """Build the package for distribution."""
        print("🔨 Building package...")
        
        try:
            # Try using build module first
            result = subprocess.run([
                sys.executable, '-m', 'build'
            ], cwd=self.project_root, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print("✅ Package built successfully using 'build' module")
                return True
            else:
                print("⚠️  'build' module failed, trying setup.py...")
                
                # Fallback to setup.py
                result = subprocess.run([
                    sys.executable, 'setup.py', 'sdist', 'bdist_wheel'
                ], cwd=self.project_root, capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    print("✅ Package built successfully using setup.py")
                    return True
                else:
                    print(f"❌ Build failed: {result.stderr}")
                    return False
        
        except subprocess.TimeoutExpired:
            print("❌ Build timed out")
            return False
        except Exception as e:
            print(f"❌ Build error: {e}")
            return False
    
    def validate_built_package(self) -> bool:
        """Validate the built package."""
        print("🔍 Validating built package...")
        
        if not self.dist_dir.exists():
            print("❌ dist/ directory not found")
            return False
        
        # Check for wheel and source distribution
        wheel_files = list(self.dist_dir.glob("*.whl"))
        tar_files = list(self.dist_dir.glob("*.tar.gz"))
        
        if not wheel_files:
            print("❌ No wheel (.whl) file found")
            return False
        
        if not tar_files:
            print("❌ No source distribution (.tar.gz) file found")
            return False
        
        print(f"✅ Found wheel: {wheel_files[0].name}")
        print(f"✅ Found source dist: {tar_files[0].name}")
        
        # Validate package with twine check
        try:
            result = subprocess.run([
                sys.executable, '-m', 'twine', 'check', str(self.dist_dir / "*")
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ Package validation passed (twine check)")
                return True
            else:
                print(f"❌ Package validation failed: {result.stderr}")
                return False
        
        except subprocess.CalledProcessError:
            print("⚠️  twine not available, skipping validation")
            return True
        except Exception as e:
            print(f"⚠️  Validation error: {e}")
            return True
    
    def test_installation(self) -> bool:
        """Test package installation in a clean environment."""
        print("🧪 Testing package installation...")
        
        wheel_files = list(self.dist_dir.glob("*.whl"))
        if not wheel_files:
            print("❌ No wheel file found for testing")
            return False
        
        wheel_file = wheel_files[0]
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                venv_dir = Path(temp_dir) / "test_venv"
                
                # Create virtual environment
                result = subprocess.run([
                    sys.executable, '-m', 'venv', str(venv_dir)
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    print(f"❌ Failed to create test venv: {result.stderr}")
                    return False
                
                # Determine python executable
                if os.name == 'nt':  # Windows
                    python_exe = venv_dir / "Scripts" / "python.exe"
                else:  # Unix-like
                    python_exe = venv_dir / "bin" / "python"
                
                # Install the wheel
                result = subprocess.run([
                    str(python_exe), '-m', 'pip', 'install', str(wheel_file)
                ], capture_output=True, text=True, timeout=120)
                
                if result.returncode != 0:
                    print(f"❌ Failed to install wheel: {result.stderr}")
                    return False
                
                # Test import
                result = subprocess.run([
                    str(python_exe), '-c', 'import src.cli; print("Import successful")'
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    print(f"❌ Failed to import package: {result.stderr}")
                    return False
                
                if "Import successful" not in result.stdout:
                    print("❌ Package import test failed")
                    return False
                
                print("✅ Package installation test passed")
                return True
        
        except Exception as e:
            print(f"❌ Installation test error: {e}")
            return False
    
    def generate_upload_instructions(self):
        """Generate instructions for uploading to PyPI."""
        print("\n" + "=" * 60)
        print("📦 PyPI UPLOAD INSTRUCTIONS")
        print("=" * 60)
        
        print("\n🔐 Prerequisites:")
        print("1. Create PyPI account: https://pypi.org/account/register/")
        print("2. Create API token: https://pypi.org/manage/account/token/")
        print("3. Configure ~/.pypirc with your credentials")
        
        print("\n📤 Upload Commands:")
        print("# Test upload to TestPyPI (recommended first)")
        print("python -m twine upload --repository testpypi dist/*")
        print("")
        print("# Production upload to PyPI")
        print("python -m twine upload dist/*")
        
        print("\n🔧 Configuration Example (~/.pypirc):")
        print("""[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-your-api-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-test-api-token-here""")
        
        print("\n✅ Verification:")
        print("# After upload, test installation from PyPI")
        print("pip install aws-ssm-calendar-generator")
        print("aws-ssm-calendar --help")
        
        print("\n⚠️  Important Notes:")
        print("- Version numbers cannot be reused on PyPI")
        print("- Test on TestPyPI first before production upload")
        print("- Ensure all tests pass before uploading")
        print("- Update documentation after successful upload")
    
    def prepare_for_pypi(self) -> bool:
        """Complete PyPI preparation process."""
        print("🚀 Preparing package for PyPI publication")
        print("=" * 50)
        
        # Step 1: Clean artifacts
        self.clean_build_artifacts()
        
        # Step 2: Validate structure
        if not self.validate_package_structure():
            return False
        
        # Step 3: Validate metadata
        if not self.validate_metadata():
            return False
        
        # Step 4: Build package
        if not self.build_package():
            return False
        
        # Step 5: Validate built package
        if not self.validate_built_package():
            return False
        
        # Step 6: Test installation
        if not self.test_installation():
            return False
        
        # Step 7: Generate upload instructions
        self.generate_upload_instructions()
        
        print("\n🎉 PyPI preparation completed successfully!")
        print("📦 Package is ready for PyPI upload")
        
        return True


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="PyPI Package Preparation")
    parser.add_argument('--project-root', help='Project root directory')
    parser.add_argument('--clean-only', action='store_true', help='Only clean build artifacts')
    parser.add_argument('--build-only', action='store_true', help='Only build the package')
    parser.add_argument('--test-only', action='store_true', help='Only test installation')
    
    args = parser.parse_args()
    
    # Initialize PyPI preparation
    pypi_prep = PyPIPreparation(args.project_root)
    
    if args.clean_only:
        pypi_prep.clean_build_artifacts()
        return 0
    
    if args.build_only:
        pypi_prep.clean_build_artifacts()
        success = pypi_prep.build_package()
        return 0 if success else 1
    
    if args.test_only:
        success = pypi_prep.test_installation()
        return 0 if success else 1
    
    # Full preparation
    success = pypi_prep.prepare_for_pypi()
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())