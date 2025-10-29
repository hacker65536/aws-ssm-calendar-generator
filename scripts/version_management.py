#!/usr/bin/env python3
"""
Version Management Script for AWS SSM Change Calendar ICS Generator

This script helps manage version numbers across different files and prepare releases.
"""

import os
import sys
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class VersionManager:
    """Manages version numbers and release preparation."""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root or os.getcwd())
        self.version_files = {
            'pyproject.toml': r'version\s*=\s*["\']([^"\']+)["\']',
            'setup.py': r'version\s*=\s*["\']([^"\']+)["\']',
        }
    
    def get_current_version(self) -> Optional[str]:
        """Get current version from pyproject.toml."""
        pyproject_file = self.project_root / "pyproject.toml"
        if not pyproject_file.exists():
            return None
        
        content = pyproject_file.read_text(encoding='utf-8')
        pattern = self.version_files['pyproject.toml']
        match = re.search(pattern, content)
        
        return match.group(1) if match else None
    
    def update_version(self, new_version: str) -> Dict[str, bool]:
        """Update version in all relevant files."""
        results = {}
        
        for file_name, pattern in self.version_files.items():
            file_path = self.project_root / file_name
            if not file_path.exists():
                results[file_name] = False
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Update version using regex
                new_content = re.sub(
                    pattern,
                    f'version = "{new_version}"',
                    content
                )
                
                if new_content != content:
                    file_path.write_text(new_content, encoding='utf-8')
                    results[file_name] = True
                else:
                    results[file_name] = False
                    
            except Exception as e:
                print(f"Error updating {file_name}: {e}")
                results[file_name] = False
        
        return results
    
    def validate_version_format(self, version: str) -> bool:
        """Validate version format (semantic versioning)."""
        pattern = r'^\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*)?(?:\+[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*)?$'
        return bool(re.match(pattern, version))
    
    def get_git_info(self) -> Dict[str, str]:
        """Get Git information for release."""
        try:
            # Get current branch
            branch = subprocess.check_output(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=self.project_root,
                text=True
            ).strip()
            
            # Get current commit hash
            commit_hash = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.project_root,
                text=True
            ).strip()
            
            # Get short commit hash
            short_hash = subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd=self.project_root,
                text=True
            ).strip()
            
            # Check if working directory is clean
            status = subprocess.check_output(
                ['git', 'status', '--porcelain'],
                cwd=self.project_root,
                text=True
            ).strip()
            
            return {
                'branch': branch,
                'commit_hash': commit_hash,
                'short_hash': short_hash,
                'is_clean': len(status) == 0,
                'status': status
            }
            
        except subprocess.CalledProcessError:
            return {
                'branch': 'unknown',
                'commit_hash': 'unknown',
                'short_hash': 'unknown',
                'is_clean': False,
                'status': 'Git not available'
            }
    
    def create_git_tag(self, version: str, message: Optional[str] = None) -> bool:
        """Create a Git tag for the version."""
        try:
            tag_name = f"v{version}"
            tag_message = message or f"Release version {version}"
            
            # Create annotated tag
            subprocess.check_call([
                'git', 'tag', '-a', tag_name, '-m', tag_message
            ], cwd=self.project_root)
            
            print(f"✅ Created Git tag: {tag_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create Git tag: {e}")
            return False
    
    def update_changelog(self, version: str, release_date: Optional[str] = None) -> bool:
        """Update CHANGELOG.md with new version."""
        changelog_file = self.project_root / "CHANGELOG.md"
        if not changelog_file.exists():
            print("❌ CHANGELOG.md not found")
            return False
        
        try:
            content = changelog_file.read_text(encoding='utf-8')
            release_date = release_date or datetime.now().strftime('%Y-%m-%d')
            
            # Replace [Unreleased] with version and date
            unreleased_pattern = r'## \[Unreleased\]'
            replacement = f'## [Unreleased]\n\n### Added\n- Future enhancements will be listed here\n\n### Changed\n- Future changes will be listed here\n\n### Fixed\n- Future fixes will be listed here\n\n## [{version}] - {release_date}'
            
            new_content = re.sub(unreleased_pattern, replacement, content, count=1)
            
            if new_content != content:
                changelog_file.write_text(new_content, encoding='utf-8')
                print(f"✅ Updated CHANGELOG.md for version {version}")
                return True
            else:
                print("⚠️  CHANGELOG.md already up to date")
                return True
                
        except Exception as e:
            print(f"❌ Failed to update CHANGELOG.md: {e}")
            return False
    
    def prepare_release(self, version: str, create_tag: bool = True, update_changelog: bool = True) -> bool:
        """Prepare a complete release."""
        print(f"🚀 Preparing release for version {version}")
        print("=" * 50)
        
        # Validate version format
        if not self.validate_version_format(version):
            print(f"❌ Invalid version format: {version}")
            print("   Expected format: X.Y.Z or X.Y.Z-prerelease+build")
            return False
        
        # Get Git info
        git_info = self.get_git_info()
        print(f"📋 Git Info:")
        print(f"   Branch: {git_info['branch']}")
        print(f"   Commit: {git_info['short_hash']}")
        print(f"   Clean: {'Yes' if git_info['is_clean'] else 'No'}")
        
        if not git_info['is_clean']:
            print("⚠️  Working directory is not clean:")
            print(f"   {git_info['status']}")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                print("❌ Release preparation cancelled")
                return False
        
        # Update version in files
        print(f"\n📝 Updating version to {version}...")
        update_results = self.update_version(version)
        
        for file_name, success in update_results.items():
            status = "✅" if success else "❌"
            print(f"   {status} {file_name}")
        
        if not any(update_results.values()):
            print("❌ Failed to update any version files")
            return False
        
        # Update changelog
        if update_changelog:
            print(f"\n📄 Updating CHANGELOG.md...")
            changelog_success = self.update_changelog(version)
            if not changelog_success:
                print("⚠️  Failed to update CHANGELOG.md")
        
        # Create Git tag
        if create_tag:
            print(f"\n🏷️  Creating Git tag...")
            tag_success = self.create_git_tag(version)
            if not tag_success:
                print("⚠️  Failed to create Git tag")
        
        print(f"\n🎉 Release preparation completed for version {version}")
        print("\n📋 Next steps:")
        print("   1. Review the changes")
        print("   2. Commit the version updates")
        print("   3. Push the changes and tags")
        print("   4. Create a GitHub release")
        print("   5. Publish to PyPI (if applicable)")
        
        return True
    
    def show_current_status(self):
        """Show current version and Git status."""
        print("📊 Current Project Status")
        print("=" * 30)
        
        # Current version
        current_version = self.get_current_version()
        print(f"Version: {current_version or 'Unknown'}")
        
        # Git info
        git_info = self.get_git_info()
        print(f"Branch: {git_info['branch']}")
        print(f"Commit: {git_info['short_hash']}")
        print(f"Clean: {'Yes' if git_info['is_clean'] else 'No'}")
        
        if not git_info['is_clean']:
            print(f"Status: {git_info['status']}")
        
        # Check if files exist
        print(f"\nFiles:")
        for file_name in self.version_files.keys():
            file_path = self.project_root / file_name
            exists = "✅" if file_path.exists() else "❌"
            print(f"  {exists} {file_name}")
        
        changelog_exists = "✅" if (self.project_root / "CHANGELOG.md").exists() else "❌"
        print(f"  {changelog_exists} CHANGELOG.md")


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Version Management for AWS SSM Calendar ICS Generator")
    parser.add_argument('--project-root', help='Project root directory')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show current status')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update version')
    update_parser.add_argument('version', help='New version number')
    
    # Release command
    release_parser = subparsers.add_parser('release', help='Prepare release')
    release_parser.add_argument('version', help='Release version number')
    release_parser.add_argument('--no-tag', action='store_true', help='Skip Git tag creation')
    release_parser.add_argument('--no-changelog', action='store_true', help='Skip changelog update')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize version manager
    vm = VersionManager(args.project_root)
    
    if args.command == 'status':
        vm.show_current_status()
        return 0
    
    elif args.command == 'update':
        if not vm.validate_version_format(args.version):
            print(f"❌ Invalid version format: {args.version}")
            return 1
        
        results = vm.update_version(args.version)
        success = any(results.values())
        
        for file_name, result in results.items():
            status = "✅" if result else "❌"
            print(f"{status} {file_name}")
        
        return 0 if success else 1
    
    elif args.command == 'release':
        success = vm.prepare_release(
            args.version,
            create_tag=not args.no_tag,
            update_changelog=not args.no_changelog
        )
        return 0 if success else 1
    
    return 1


if __name__ == '__main__':
    exit(main())