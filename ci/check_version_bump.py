#!/usr/bin/env python

"""Script that checks if a version bump is needed, and whether it has been made.

Checks are based on which files have been changed, indicating potential incompatibility
between versions.
"""

import fnmatch
import sys


FILES_CAUSING_INCOMPATIBILITY = [
    'cuebot/src/main/resources/conf/ddl/postgres/migrations/*.sql',
]

VERSION_FILE = 'VERSION.in'


def main():
    changed_files = sys.argv[1:]

    violating_files = []
    version_file_updated = False

    for changed_file in changed_files:
        print('changed file: %s' % changed_file)

        if changed_file == VERSION_FILE:
            version_file_updated = True

        for glob_to_check in FILES_CAUSING_INCOMPATIBILITY:
            if fnmatch.fnmatch(changed_file, glob_to_check):
                violating_files.append(changed_file)

    if violating_files and not version_file_updated:
        print(
            'Files were changed which indicate version incompatibility, but the OpenCue minor '
            'version number was not updated.')
        print('Violating files: \n  %s' % '\n  '.join(violating_files))
        sys.exit(1)


if __name__ == '__main__':
    main()
