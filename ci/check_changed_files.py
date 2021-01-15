#!/usr/bin/env python

"""Script that checks if files were changed which should not be.

This script is meant to be run in the context or GitHub Actions, and expects all changed files
to be passed via commandline, like:

  $ ci/check_changed_files.py file/that/was/changed.txt other/file/changed.py
"""

import fnmatch
import sys


FILES_THAT_SHOULD_NOT_BE_CHANGED = [
    ('cuebot/src/main/resources/conf/ddl/postgres/migrations/*.sql', 'add a new migration file'),
    ('cuebot/src/main/resources/public/dtd/*.dtd', 'add a new schema version'),
]


def main():
    changed_files = sys.argv[1:]

    violating_files = False

    for changed_file in changed_files:
        for glob_to_check, suggestion in FILES_THAT_SHOULD_NOT_BE_CHANGED:
            if fnmatch.fnmatch(changed_file, glob_to_check):
                violating_files = True
                print('File %s should not be modified. Suggestion: %s' % (changed_file, suggestion))

    if violating_files:
        sys.exit(1)


if __name__ == '__main__':
    main()
