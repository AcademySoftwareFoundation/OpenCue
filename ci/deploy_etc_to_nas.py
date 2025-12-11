#!/usr/bin/env python3
"""
Deploy etc configuration files to NAS
This script backs up existing files and copies new configuration files
"""

import argparse
import shutil
import sys
from pathlib import Path


def main():
    try:
        return _do()
    except Exception as e:
        print(f"ERROR: Deployment failed: {e}", file=sys.stderr)
        return 1


def _do():
    parser = argparse.ArgumentParser(
        description="Deploy etc configuration files to NAS"
    )
    parser.add_argument(
        "--source-path",
        default="etc",
        help="Source directory containing files to deploy (default: etc)",
    )
    parser.add_argument(
        "--destination-path",
        default=r"\\ubisoft.org\mtlstudio\Helix\tools\opencue\etc",
        help="Network destination path",
    )

    args = parser.parse_args()

    # Determine repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    source_full_path = repo_root / args.source_path
    destination_path = Path(args.destination_path)

    print(f"Repository root: {repo_root}")
    print(f"Source path: {source_full_path}")
    print(f"Destination path: {destination_path}")

    # Validate source directory exists
    if not source_full_path.exists():
        print(
            f"ERROR: Source directory does not exist: {source_full_path}",
            file=sys.stderr,
        )
        return 1

    # Validate destination directory exists
    if not destination_path.exists():
        print(
            f"ERROR: Destination directory does not exist or is not accessible: {destination_path}",
            file=sys.stderr,
        )
        return 1

    source_files = [path for path in source_full_path.rglob("*") if path.is_file()]
    if not source_files:
        print(
            f"ERROR: No files found in source directory: {source_full_path}",
            file=sys.stderr,
        )
        return 1

    backup_path = destination_path / ".BKP"

    # Handle backup directory
    if backup_path.exists():
        print(f"Backup directory exists, clearing contents: {backup_path}")
        shutil.rmtree(backup_path)

    # Backup existing files
    existing_files = [path for path in destination_path.rglob("*") if path.is_file()]

    if existing_files:
        print(f"Creating backup directory: {backup_path}")
        backup_path.mkdir(parents=True)
        print(f"Backing up {len(existing_files)} existing files to {backup_path}")
        for file_path in existing_files:
            relative_path = file_path.relative_to(destination_path)
            backup_file_path = backup_path / relative_path
            backup_file_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_file_path)
            print(f"  Backed up: {relative_path}")

    else:
        print("No existing files to backup")

    # delete files in destination
    print(f"Deleting existing files in destination: {destination_path}")
    for file_path in existing_files:
        relative_path = file_path.relative_to(destination_path)
        file_path.unlink()
        print(f"  Deleted: {relative_path}")

    # Copy new files
    print(f"Copying {len(source_files)} files from source to destination")

    for file_path in source_files:
        relative_path = file_path.relative_to(source_full_path)
        dest_file = destination_path / relative_path

        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, dest_file)
        print(f"  Copied: {relative_path}")

    print("Deployment completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
