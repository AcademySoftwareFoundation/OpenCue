#!/usr/bin/env python

"""Script that checks database migration files for validity.

Ensures migration filenames are correct and that each database version has one and only one
file associated with it.
"""

import glob
import os
import re
import sys


MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'cuebot/src/main/resources/conf/ddl/postgres/migrations')

MIGRATION_FILENAME_REGEX = re.compile(r'^V(?P<version_number>[\d]+)__.*\.sql$')


def main():
    if not os.path.exists(MIGRATIONS_DIR):
        print('Migrations directory was not found, expected at %s' % MIGRATIONS_DIR)
        sys.exit(1)

    version_numbers_seen = {}

    for migration_file in glob.glob(os.path.join(MIGRATIONS_DIR, '*.sql')):
        version_match = MIGRATION_FILENAME_REGEX.match(os.path.basename(migration_file))
        if not version_match:
            print(
                'Migration file %s did not match expected format, should be '
                '"V<version_number>__<description>.sql"')
            sys.exit(1)
        if version_match.group('version_number') not in version_numbers_seen:
            version_numbers_seen[version_match.group('version_number')] = []
        version_numbers_seen[version_match.group('version_number')].append(
            os.path.basename(migration_file))

    violation_found = False
    for version_number, filenames in list(version_numbers_seen.items()):
        if len(filenames) > 1:
            violation_found = True
            print(
                'Migration version %s has multiple files associated. Conflicting files: %s' % (
                    version_number, ', '.join(filenames)))

    if violation_found:
        sys.exit(1)


if __name__ == '__main__':
    main()
