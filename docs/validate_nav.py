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

"""Validates the navigation front matter of the OpenCue documentation site.

just-the-docs sorts ``nav_order`` within each sibling group -- pages sharing the same
``parent`` and ``grand_parent`` -- and never across groups. This script enforces the rules
that follow from that model so a broken navigation fails the build instead of rendering in
an unspecified order.

Run from the ``docs`` directory::

    python3 validate_nav.py

Exits non-zero when any error is found. Use ``--warnings-as-errors`` in stricter contexts.
"""

import argparse
import os
import re
import sys
from collections import defaultdict

# Collections that just-the-docs renders as a navigation tree. Each is an independent
# namespace: a `parent` in one tree never resolves to a page in another.
NAV_COLLECTIONS = ('_docs',)

# Collections ordered by date rather than by `nav_order`. News entries take their date from
# the filename prefix, which Jekyll parses for any collection document. Release filenames are
# named after the version they announce, so those declare `date` in front matter instead.
DATED_COLLECTIONS = {
    '_news': 'filename',
    '_releases': 'front-matter',
}

# Top-level pages live at the root of the docs directory and form their own tree.
PAGE_TREE = 'pages'

# Root markdown files that `exclude` in _config.yml keeps out of the built site.
NOT_PUBLISHED = ('README.md', 'DOCKER.md', 'CONTRIBUTING.md')

DATED_FILENAME_RE = re.compile(r'^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$')
ISO_DATE_RE = re.compile(r'\d{4}-\d{2}-\d{2}')

FRONT_MATTER_KEY_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$')


class Page:
    """A markdown file's navigation-relevant front matter."""

    def __init__(self, path, tree, data):
        self.path = path
        self.tree = tree
        self.data = data

    @property
    def title(self):
        return self.data.get('title')

    @property
    def parent(self):
        return self.data.get('parent')

    @property
    def grand_parent(self):
        return self.data.get('grand_parent')

    @property
    def nav_order(self):
        return self.data.get('nav_order')

    @property
    def has_children(self):
        return self.data.get('has_children') == 'true'

    @property
    def nav_exclude(self):
        return self.data.get('nav_exclude') == 'true'

    @property
    def group(self):
        """The sibling group this page is sorted within."""
        return (self.tree, self.grand_parent, self.parent)


def parse_front_matter(path):
    """Extracts top-level scalar keys from a file's YAML front matter.

    Indented lines are continuations of block scalars such as ``description: >`` and carry no
    navigation meaning, so they are skipped. Returns None when the file has no front matter.
    """
    with open(path, 'r', encoding='utf-8') as handle:
        if handle.readline().rstrip('\n') != '---':
            return None
        data = {}
        for line in handle:
            stripped = line.rstrip('\n')
            if stripped == '---':
                return data
            if not stripped or stripped[0].isspace() or stripped.startswith('#'):
                continue
            match = FRONT_MATTER_KEY_RE.match(stripped)
            if match:
                value = match.group(2).strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
                    value = value[1:-1]
                data[match.group(1)] = value
    return None


def collect(docs_dir):
    """Loads every page that participates in navigation, keyed by tree."""
    pages = defaultdict(list)
    malformed = []

    for name in sorted(os.listdir(docs_dir)):
        if name in NOT_PUBLISHED:
            continue
        if name.endswith('.md') and os.path.isfile(os.path.join(docs_dir, name)):
            path = os.path.join(docs_dir, name)
            data = parse_front_matter(path)
            if data is None:
                malformed.append(path)
            else:
                pages[PAGE_TREE].append(Page(path, PAGE_TREE, data))

    for collection in tuple(NAV_COLLECTIONS) + tuple(DATED_COLLECTIONS):
        root = os.path.join(docs_dir, collection)
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for filename in sorted(filenames):
                if not filename.endswith('.md'):
                    continue
                path = os.path.join(dirpath, filename)
                data = parse_front_matter(path)
                if data is None:
                    malformed.append(path)
                else:
                    pages[collection].append(Page(path, collection, data))

    return pages, malformed


def check_sibling_order(pages, errors):
    """Sibling pages sharing a nav_order render in an unspecified order."""
    groups = defaultdict(list)
    for page in pages:
        if page.title and not page.nav_exclude:
            groups[page.group].append(page)

    for group, members in sorted(groups.items(), key=lambda item: str(item[0])):
        seen = defaultdict(list)
        for page in members:
            if page.nav_order is None:
                continue
            if not re.fullmatch(r'-?\d+', page.nav_order):
                errors.append(
                    '%s: nav_order %r is not an integer' % (page.path, page.nav_order))
                continue
            seen[int(page.nav_order)].append(page)

        for order, tied in sorted(seen.items()):
            if len(tied) > 1:
                where = 'parent %r' % group[2] if group[2] else 'the top level of %r' % group[0]
                errors.append(
                    'duplicate nav_order %d under %s:\n%s'
                    % (order, where, '\n'.join('        %s' % p.path for p in sorted(
                        tied, key=lambda p: p.path))))


def check_parents(pages, errors, warnings):
    """`parent` and `grand_parent` must resolve to a page that declares has_children."""
    by_title = defaultdict(list)
    for page in pages:
        if page.title:
            by_title[page.title].append(page)

    for page in pages:
        if not page.title or not page.parent:
            continue

        candidates = by_title.get(page.parent)
        if not candidates:
            errors.append(
                '%s: parent %r does not match the title of any page in this tree'
                % (page.path, page.parent))
            continue

        if not any(candidate.has_children for candidate in candidates):
            errors.append(
                '%s: parent %r exists but does not set has_children: true'
                % (page.path, page.parent))

        if page.grand_parent:
            if not any(c.parent == page.grand_parent for c in candidates):
                errors.append(
                    '%s: grand_parent %r is not the parent of %r'
                    % (page.path, page.grand_parent, page.parent))
        elif all(candidate.parent for candidate in candidates):
            errors.append(
                '%s: parent %r is itself nested, so grand_parent must be set'
                % (page.path, page.parent))

    for page in pages:
        if page.has_children and not any(other.parent == page.title for other in pages):
            warnings.append('%s: has_children: true but no page declares it as a parent'
                            % page.path)


def check_directory_matches_section(collection, docs_dir, pages, warnings):
    """A page's directory should match the section it renders under.

    The navigation is built from front matter alone, so a file can sit in one directory and
    appear under an unrelated section. That drift is legal but makes pages hard to find, so
    it is reported.
    """
    section_by_dir = {}
    for page in pages:
        relative = os.path.relpath(page.path, os.path.join(docs_dir, collection))
        parts = relative.split(os.sep)
        if len(parts) == 2 and parts[1] == 'index.md' and page.title and not page.parent:
            section_by_dir[parts[0]] = page.title

    titles = {page.title: page for page in pages if page.title}

    for page in pages:
        relative = os.path.relpath(page.path, os.path.join(docs_dir, collection))
        parts = relative.split(os.sep)
        if len(parts) < 2 or parts[0] not in section_by_dir:
            continue
        if relative == os.path.join(parts[0], 'index.md'):
            continue

        # Walk up the parent chain to the section this page actually renders under.
        root, seen = page.parent, set()
        while root in titles and titles[root].parent and root not in seen:
            seen.add(root)
            root = titles[root].parent

        expected = section_by_dir[parts[0]]
        if root and root != expected:
            warnings.append(
                '%s: sits under %s/ but renders in %r; move the file or fix its parent'
                % (page.path, parts[0], root))


def check_dated_collection(collection, source, pages, errors):
    """Dated entries sort by date, so they must carry a date and no ordering front matter."""
    for page in pages:
        if source == 'filename':
            if not DATED_FILENAME_RE.match(os.path.basename(page.path)):
                errors.append(
                    '%s: %s entries must be named YYYY-MM-DD-slug.md so Jekyll derives the date'
                    % (page.path, collection))
        else:
            date = page.data.get('date')
            if not date or not ISO_DATE_RE.fullmatch(date):
                errors.append(
                    '%s: %s entries are sorted by date; add `date: YYYY-MM-DD` to the front matter'
                    % (page.path, collection))

        for field in ('nav_order', 'parent', 'grand_parent'):
            if page.data.get(field) is not None:
                errors.append(
                    '%s: %s entries are ordered by date; remove %s'
                    % (page.path, collection, field))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        '--warnings-as-errors', action='store_true', help='exit non-zero on warnings too')
    args = parser.parse_args()

    docs_dir = os.path.dirname(os.path.abspath(__file__))
    pages, malformed = collect(docs_dir)

    errors = ['%s: missing or unterminated YAML front matter' % path for path in malformed]
    warnings = []

    for tree in (PAGE_TREE,) + NAV_COLLECTIONS:
        if tree in pages:
            check_sibling_order(pages[tree], errors)
            check_parents(pages[tree], errors, warnings)

    for collection in NAV_COLLECTIONS:
        if collection in pages:
            check_directory_matches_section(collection, docs_dir, pages[collection], warnings)

    for collection, source in DATED_COLLECTIONS.items():
        if collection in pages:
            check_dated_collection(collection, source, pages[collection], errors)

    total = sum(len(group) for group in pages.values())
    print('Checked %d markdown files across %d navigation trees.'
          % (total, len([t for t in pages if pages[t]])))

    for warning in warnings:
        print('  WARNING %s' % warning)
    for error in errors:
        print('  ERROR   %s' % error)

    if errors or (warnings and args.warnings_as_errors):
        print('\nNavigation validation failed: %d error(s), %d warning(s).'
              % (len(errors), len(warnings)))
        print('See the "Navigation" section of docs/README.md for the ordering rules.')
        return 1

    print('Navigation validation passed (%d warning(s)).' % len(warnings))
    return 0


if __name__ == '__main__':
    sys.exit(main())
