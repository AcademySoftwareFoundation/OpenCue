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

"""Fix numbering in nav_order_index.txt by renumbering entries sequentially."""

import os

def fix_nav_order_numbers(file_path: str) -> None:
    """Read nav_order_index.txt and renumber entries sequentially."""

    with open(file_path, 'r') as f:
        lines = f.readlines()

    output_lines = []
    counter = 1

    for line in lines:
        stripped = line.strip()

        # Preserve empty lines and comments
        if not stripped or stripped.startswith('#'):
            output_lines.append(line)
            continue

        # Parse data lines (format: number|path)
        if '|' in stripped:
            parts = stripped.split('|', 1)
            if len(parts) == 2:
                path = parts[1]
                output_lines.append(f"{counter}|{path}\n")
                counter += 1
            else:
                # Malformed line, keep as-is
                output_lines.append(line)
        else:
            # Not a data line, keep as-is
            output_lines.append(line)

    # Write back to file
    with open(file_path, 'w') as f:
        f.writelines(output_lines)

    print(f"Fixed numbering: {counter - 1} entries renumbered sequentially")


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    index_file = os.path.join(script_dir, 'nav_order_index.txt')

    if not os.path.exists(index_file):
        print(f"Error: {index_file} not found")
        exit(1)

    fix_nav_order_numbers(index_file)
