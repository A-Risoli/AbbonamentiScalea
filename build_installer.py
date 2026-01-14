#!/usr/bin/env python3
"""
Build script for AbbonamentiScalea Windows installer using PyInstaller.

This script automates the process of building a standalone Windows executable
for the Abbonamenti application. It handles all necessary PyInstaller options
for bundling PyQt6 and matplotlib dependencies.

Usage:
    python build_installer.py [--onefile] [--debug]

Options:
    --onefile   Create a single executable file (slower startup, but portable)
    --debug     Build with console window for debugging
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    """Build the Windows installer using PyInstaller."""
    parser = argparse.ArgumentParser(description="Build AbbonamentiScalea installer")
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Create single .exe file (default: onedir bundle)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Build with console window for debugging",
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent
    main_script = project_root / "abbonamenti" / "main.py"
    
    if not main_script.exists():
        print(f"❌ Error: Main script not found at {main_script}")
        sys.exit(1)

    # Clean previous builds
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    
    print("🧹 Cleaning previous builds...")
    for directory in [dist_dir, build_dir]:
        if directory.exists():
            shutil.rmtree(directory)
            print(f"   Removed {directory}")

    # Build PyInstaller command (use uv run to ensure correct environment)
    cmd = [
        "uv",
        "run",
        "pyinstaller",
        "--name=AbbonamentiScalea",
        "--clean",
        "--noconfirm",
        "--log-level=INFO",
    ]

    # Add onefile or onedir
    if args.onefile:
        cmd.append("--onefile")
        print("📦 Building single .exe file (slower startup)...")
    else:
        cmd.append("--onedir")
        print("📦 Building application bundle (faster startup, recommended)...")

    # Add windowed or console
    if args.debug:
        print("🐛 Debug mode: console window enabled")
    else:
        cmd.append("--windowed")
        print("🖼️  Windowed mode: no console window")

    # Hidden imports for matplotlib
    cmd.extend([
        "--hidden-import=matplotlib.backends.backend_qtagg",
        "--hidden-import=PyQt6.sip",
    ])

    # Collect matplotlib data files
    cmd.append("--collect-data=matplotlib")

    # Add icon if it exists
    icon_path = project_root / "assets" / "icon.ico"
    if icon_path.exists():
        cmd.append(f"--icon={icon_path}")
        print(f"📎 Using icon: {icon_path}")
    else:
        print(f"ℹ️  No icon found at {icon_path} (optional)")

    # Add main script
    cmd.append(str(main_script))

    print(f"\n🔨 Running PyInstaller...")
    print(f"   Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, cwd=project_root, check=True)
        
        print("\n" + "=" * 60)
        print("✅ Build successful!")
        print("=" * 60)
        
        if args.onefile:
            exe_path = dist_dir / "AbbonamentiScalea.exe"
            print(f"\n📍 Executable: {exe_path}")
            print(f"   Size: {exe_path.stat().st_size / (1024 * 1024):.1f} MB")
        else:
            exe_path = dist_dir / "AbbonamentiScalea" / "AbbonamentiScalea.exe"
            print(f"\n📍 Application bundle: {dist_dir / 'AbbonamentiScalea'}")
            print(f"   Executable: {exe_path}")
            if exe_path.exists():
                print(f"   Size: {exe_path.stat().st_size / (1024 * 1024):.1f} MB")
        
        print("\n📋 Next steps:")
        print("   1. Test the executable by running it")
        print("   2. Verify database creation in %APPDATA%\\AbbonamentiScalea")
        print("   3. Test all features (add/edit/delete, statistics, export)")
        
        if not args.onefile:
            print("   4. Distribute the entire 'dist/AbbonamentiScalea' folder")
        
        print("\n💡 To create an installer, consider using:")
        print("   - Inno Setup: https://jrsoftware.org/isinfo.php")
        print("   - NSIS: https://nsis.sourceforge.io/")
        
        return 0
        
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 60)
        print("❌ Build failed!")
        print("=" * 60)
        print(f"\n   Error code: {e.returncode}")
        print("\n💡 Troubleshooting:")
        print("   - Ensure all dependencies are installed: uv sync")
        print("   - Check the build log above for specific errors")
        print("   - Try running with --debug flag for more details")
        return 1
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
