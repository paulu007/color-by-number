#!/usr/bin/env python3
"""
Nuitka Build Configuration Script
Run this locally to build the executable

Usage:
    python build_config.py
    python build_config.py --onefile
    python build_config.py --debug
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path


def get_nuitka_command(onefile=False, debug=False):
    """Generate Nuitka command with all options"""
    
    # Base command
    cmd = [
        sys.executable, "-m", "nuitka",
    ]
    
    # Build mode
    if onefile:
        cmd.append("--onefile")
        cmd.append("--onefile-tempdir-spec=%TEMP%\\ColorByNumber")
    else:
        cmd.append("--standalone")
    
    # Windows options
    cmd.extend([
        "--windows-console-mode=disable",  # No console window
    ])
    
    # Icon (if exists)
    icon_path = Path("assets/icon.ico")
    if icon_path.exists():
        cmd.append(f"--windows-icon-from-ico={icon_path}")
    
    # Plugins
    cmd.extend([
        "--enable-plugin=tk-inter",   # Tkinter support
        "--enable-plugin=numpy",       # NumPy optimization
    ])
    
    # Include packages
    cmd.extend([
        "--include-package=PIL",
        "--include-package=sklearn",
        "--include-package=cv2",
        "--include-package=scipy",
        "--include-package=numpy",
    ])
    
    # Include data files
    cmd.extend([
        "--include-package-data=sklearn",
        "--include-package-data=cv2",
    ])
    
    # Exclude unnecessary packages
    cmd.extend([
        "--nofollow-import-to=pytest",
        "--nofollow-import-to=matplotlib",
        "--nofollow-import-to=IPython",
        "--nofollow-import-to=jupyter",
        "--nofollow-import-to=notebook",
        "--nofollow-import-to=sphinx",
        "--nofollow-import-to=pandas",
    ])
    
    # Output settings
    cmd.extend([
        "--output-dir=dist",
        "--output-filename=ColorByNumber.exe",
    ])
    
    # Product info
    cmd.extend([
        "--company-name=Happy Coloring",
        "--product-name=Color by Number",
        "--product-version=1.0.0",
        "--file-description=Color by Number Application",
        "--copyright=Copyright 2024",
    ])
    
    # Build options
    cmd.append("--assume-yes-for-downloads")
    cmd.append("--remove-output")
    
    if debug:
        cmd.append("--debug")
        cmd.append("--report=nuitka-report.xml")
    
    # Source file
    cmd.append("src/color_by_number.py")
    
    return cmd


def check_requirements():
    """Check if all required packages are installed"""
    required = ['nuitka', 'numpy', 'PIL', 'sklearn', 'cv2', 'scipy']
    missing = []
    
    for package in required:
        try:
            if package == 'PIL':
                __import__('PIL')
            elif package == 'sklearn':
                __import__('sklearn')
            elif package == 'cv2':
                __import__('cv2')
            else:
                __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("\nInstall with:")
        print("  pip install -r requirements.txt")
        print("  pip install nuitka zstandard ordered-set")
        return False
    
    return True


def build(onefile=False, debug=False):
    """Run the build process"""
    
    print("=" * 60)
    print("🎨 Color by Number - Nuitka Build Script")
    print("=" * 60)
    
    # Check requirements
    print("\n📋 Checking requirements...")
    if not check_requirements():
        sys.exit(1)
    print("✅ All requirements satisfied")
    
    # Get build command
    cmd = get_nuitka_command(onefile=onefile, debug=debug)
    
    # Show command
    print(f"\n🔨 Build mode: {'Onefile' if onefile else 'Standalone'}")
    print(f"📝 Command:\n{' '.join(cmd)}\n")
    
    # Run build
    print("🚀 Starting build (this may take several minutes)...\n")
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            shell=False,
        )
        
        print("\n" + "=" * 60)
        print("✅ BUILD SUCCESSFUL!")
        print("=" * 60)
        
        # Show output location
        if onefile:
            print(f"\n📦 Executable: dist/ColorByNumber.exe")
        else:
            print(f"\n📦 Output folder: dist/color_by_number.dist/")
            print(f"   Run: dist/color_by_number.dist/ColorByNumber.exe")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed with error code: {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        print("\n❌ Nuitka not found. Install with: pip install nuitka")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Build Color by Number with Nuitka")
    parser.add_argument("--onefile", action="store_true", 
                       help="Build single executable file (larger, slower start)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug mode and generate report")
    
    args = parser.parse_args()
    build(onefile=args.onefile, debug=args.debug)


if __name__ == "__main__":
    main() 