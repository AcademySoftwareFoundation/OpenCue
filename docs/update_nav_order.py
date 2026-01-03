#!/usr/bin/env python3

#  Copyright Contributors to the OpenCue Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""
Update nav_order values in markdown files based on nav_order_index.txt.

Usage:
    python update_nav_order.py [--dry-run]

Options:
    --dry-run    Show what would be changed without modifying files
"""

import re
import sys
from pathlib import Path

def read_nav_order_index(index_file):
    """Read nav_order_index.txt and return dict of {file_path: nav_order}."""
    nav_orders = {}

    with open(index_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Parse line format: nav_order|file_path
            parts = line.split('|', 1)
            if len(parts) != 2:
                print(f"Warning: Skipping invalid line: {line}")
                continue

            try:
                nav_order = int(parts[0])
                file_path = parts[1]
                nav_orders[file_path] = nav_order
            except ValueError:
                print(f"Warning: Invalid nav_order value: {parts[0]}")
                continue

    return nav_orders

def update_nav_order_in_file(file_path, new_nav_order, dry_run=False):
    """Update nav_order value in a markdown file's YAML front matter."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if file has YAML front matter
        if not content.startswith('---'):
            print(f"Warning: {file_path} has no YAML front matter")
            return False

        # Extract YAML front matter
        match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not match:
            print(f"Warning: {file_path} has invalid YAML front matter")
            return False

        front_matter = match.group(1)
        old_content = match.group(0)

        # Check if nav_order exists in front matter
        nav_order_match = re.search(r'^nav_order:\s*(\d+)', front_matter, re.MULTILINE)

        if nav_order_match:
            old_nav_order = int(nav_order_match.group(1))

            if old_nav_order == new_nav_order:
                # No change needed
                return True

            # Replace nav_order value
            new_front_matter = re.sub(
                r'^(nav_order:\s*)(\d+)',
                f'\\g<1>{new_nav_order}',
                front_matter,
                flags=re.MULTILINE
            )
        else:
            # nav_order doesn't exist, add it after title
            title_match = re.search(r'^(title:.*?)$', front_matter, re.MULTILINE)
            if title_match:
                # Add nav_order after title
                new_front_matter = re.sub(
                    r'^(title:.*?)$',
                    f'\\g<1>\\nnav_order: {new_nav_order}',
                    front_matter,
                    flags=re.MULTILINE
                )
                old_nav_order = None
            else:
                # No title found, add at the beginning
                new_front_matter = f'nav_order: {new_nav_order}\n{front_matter}'
                old_nav_order = None

        # Replace front matter in content
        new_content = content.replace(old_content, f'---\n{new_front_matter}\n---', 1)

        if dry_run:
            if nav_order_match:
                print(f"Would update {file_path}: {old_nav_order} → {new_nav_order}")
            else:
                print(f"Would add nav_order to {file_path}: → {new_nav_order}")
            return True

        # Write updated content back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        if nav_order_match:
            print(f"Updated {file_path}: {old_nav_order} → {new_nav_order}")
        else:
            print(f"Added nav_order to {file_path}: → {new_nav_order}")

        return True

    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    # Parse command line arguments
    dry_run = '--dry-run' in sys.argv

    # Get index file path
    index_file = Path(__file__).parent / 'nav_order_index.txt'

    if not index_file.exists():
        print(f"Error: Index file not found: {index_file}")
        print("Run extract_nav_orders.py first to create the index file")
        return 1

    # Read nav_order index
    print(f"Reading nav_order index from: {index_file}")
    nav_orders = read_nav_order_index(index_file)
    print(f"Found {len(nav_orders)} files in index")

    if dry_run:
        print("\n=== DRY RUN MODE ===\n")

    # Update each file
    success_count = 0
    error_count = 0

    for file_path, nav_order in nav_orders.items():
        if not Path(file_path).exists():
            print(f"Warning: File not found: {file_path}")
            error_count += 1
            continue

        if update_nav_order_in_file(file_path, nav_order, dry_run):
            success_count += 1
        else:
            error_count += 1

    # Print summary
    print(f"\n{'Would update' if dry_run else 'Updated'} {success_count} files")
    if error_count > 0:
        print(f"Encountered errors with {error_count} files")

    if dry_run:
        print("\nTo apply these changes, run without --dry-run flag")

    return 0 if error_count == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
