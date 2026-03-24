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


#!/usr/bin/env python3
"""
Script to update nav_order in news markdown files based on their dates.
The newest file gets nav_order: 0, and the oldest gets nav_order: N-1.
"""

import re
from datetime import datetime
from pathlib import Path


def extract_date_from_filename(filename):
    """Extract date from filename in format YYYY-MM-DD-*.md"""
    match = re.match(r'^(\d{4}-\d{2}-\d{2})-', filename)
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d')
    return None


def update_nav_order(file_path, nav_order):
    """Update the nav_order in a markdown file's frontmatter."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace existing nav_order
    new_content = re.sub(
        r'^(nav_order:\s*)\d+',
        f'nav_order: {nav_order}',
        content,
        flags=re.MULTILINE
    )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return new_content != content  # Return True if changed


def main():
    news_dir = Path(__file__).parent

    # Get all markdown files with dates in the filename (exclude index.md)
    news_files = []
    for file_path in news_dir.glob('*.md'):
        if file_path.name == 'index.md':
            continue

        date = extract_date_from_filename(file_path.name)
        if date:
            news_files.append((date, file_path))

    # Sort by date, newest first
    news_files.sort(key=lambda x: x[0], reverse=True)

    print(f"Found {len(news_files)} news files:\n")
    print(f"{'nav_order':<12} {'Date':<12} {'Filename'}")
    print("-" * 80)

    # Update nav_order for each file
    for nav_order, (date, file_path) in enumerate(news_files):
        changed = update_nav_order(file_path, nav_order)
        status = "(updated)" if changed else "(no change)"
        print(f"{nav_order:<12} {date.strftime('%Y-%m-%d'):<12} {file_path.name} {status}")

    print(f"\nDone! Updated nav_order for {len(news_files)} files.")


if __name__ == '__main__':
    main()
