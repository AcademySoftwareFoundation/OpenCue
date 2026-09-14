#!/usr/bin/env python
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

"""Reports Houdini license usage from sesictrl to Cuebot.

Houdini licenses issued by ``sesinetd`` are held per host: any number of frames
running on one machine draw a single license. Cuebot cannot see that on its own,
and it cannot see licenses held by artists on workstations at all. This script
closes both gaps by polling ``sesictrl`` and pushing the result into a Cuebot
limit of type HOST.

Run it from cron or a systemd timer, typically once a minute::

    * * * * * /usr/bin/flock -n /var/lock/sesictrl_report.lock \\
        /opt/opencue/samples/licensing/sesictrl_report.py \\
        --config /etc/opencue/sesictrl_limits.yaml

The limits named in the config must already exist in Cuebot and should be of
type HOST. Start them ADVISORY and soak: Cuebot will bias booking toward hosts
that already hold a license without ever holding a frame back, and you can
compare its reported usage against the license server's own numbers before
deciding whether enforcement adds anything::

    limit = opencue.api.createLimit(
        'houdini', 30, limit_pb2.HOST, limit_pb2.ADVISORY,
        exitStatus=330, delayMinutes=2)

Setting ``exitStatus`` matters as much as this script does. Layers rarely declare
the licenses they need, so a limit that only sees spec-tagged layers under-counts
the farm's own usage badly. With an exit status configured, any frame that fails
for want of a license binds its layer to the limit automatically, and coverage
grows on its own. Use the code your RQD emits via ``runner.log_exit_status_rules``
(330 by convention).

For a HOST limit the maximum is the number of *machines* the farm may spread
the license across, not the number of licenses. Setting it below the pool size
is how seats are kept free for artists.

Adapting to your site
---------------------
SideFX documents ``sesictrl print-license --format json`` but does not publish
the JSON schema, and it varies between Houdini versions. All format knowledge
lives in ``parse_sesictrl_json`` below. Capture your own output and validate the
mapping before pointing this at a live Cuebot::

    sesictrl print-license --format json --show-all > /tmp/sesi.json
    ./sesictrl_report.py --config ... --from-file /tmp/sesi.json --dry-run -vv

If ``parse_sesictrl_json`` raises or returns nothing for a product you expect,
that one function is the only thing that needs to change.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import collections
import json
import logging
import os
import subprocess
import sys
import time

import yaml

import opencue
import opencue.exception
from opencue_proto import limit_pb2


logger = logging.getLogger('sesictrl_report')

DEFAULT_CONFIG = '/etc/opencue/sesictrl_limits.yaml'
DEFAULT_SESICTRL = 'sesictrl'
DEFAULT_TIMEOUT = 30

# Exit codes. Distinct values so cron mail and monitoring can tell the failure
# modes apart.
EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_SESICTRL = 3
EXIT_PARSE = 4
EXIT_CUEBOT = 5


class ReportError(Exception):
    """Raised when usage could not be determined and nothing should be posted."""

    def __init__(self, message, exit_code):
        super(ReportError, self).__init__(message)
        self.exit_code = exit_code


# A single license checkout observed on the license server.
Checkout = collections.namedtuple('Checkout', ['product', 'host', 'user', 'tokens'])


def normalize_host(name):
    """Reduces a reported hostname to the key Cuebot matches hosts on.

    Cuebot stores short, lowercase hostnames. License servers report anything
    from a bare name to a fully qualified domain name, and sesinetd prefixes the
    account holding the license. Cuebot normalizes on its side as well, so this
    is belt and braces, but normalizing here keeps the ``--dry-run`` output
    honest about what will actually be sent.

    :type  name: str
    :param name: hostname as reported by the license server
    :rtype:  str
    :return: short lowercase hostname, or an empty string if unusable
    """
    if not name:
        return ''
    # Drop any "user@" prefix before the domain: Cuebot matches on the machine
    # alone, so a composite identity matches no host at all.
    return name.strip().rpartition('@')[2].split('.')[0].lower()


def split_identity(host_field, user_field=''):
    """Resolves the user and host a checkout belongs to.

    ``sesinetd`` names a checkout after the account holding it, as
    ``user@host``. Depending on the sesictrl version that composite arrives in
    the host field, in the user field, or split across both, so both fields are
    considered here and each half is taken from wherever it appears.

    Keeping the halves apart matters: Cuebot matches holders on the host alone,
    so a composite name matches no Cuebot host, and two artists on one machine
    would count as two machines against a HOST limit.

    :type  host_field: str
    :param host_field: value of the record's host-ish key, possibly ``user@host``
    :type  user_field: str
    :param user_field: value of the record's user-ish key, possibly ``user@host``
    :rtype:  tuple[str, str]
    :return: user (empty if none was reported) and normalized short hostname
    """
    host_user, _, host = (host_field or '').strip().rpartition('@')

    named_user, separator, user_host = (user_field or '').strip().rpartition('@')
    if not separator:
        # Without an '@', rpartition leaves the whole string on the right; for a
        # user field that string is the account, not a machine.
        named_user, user_host = user_host, ''

    return named_user or host_user, normalize_host(host or user_host)


def run_sesictrl(binary, timeout, extra_args=None):
    """Runs ``sesictrl print-license`` and returns its raw stdout.

    :type  binary: str
    :param binary: path to the sesictrl executable
    :type  timeout: int
    :param timeout: seconds to wait before giving up on the license server
    :type  extra_args: list[str]
    :param extra_args: additional arguments, e.g. ``['--host', 'lic01']``
    :rtype:  str
    :return: raw stdout from sesictrl
    :raises ReportError: if sesictrl is missing, times out, or exits non-zero
    """
    command = [binary, 'print-license', '--format', 'json', '--show-all']
    command.extend(extra_args or [])
    logger.debug('running: %s', ' '.join(command))

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            universal_newlines=True,
            check=False)
    except OSError as exc:
        raise ReportError('cannot execute %s: %s' % (binary, exc), EXIT_SESICTRL)
    except subprocess.TimeoutExpired:
        raise ReportError(
            '%s did not respond within %ds' % (binary, timeout), EXIT_SESICTRL)

    if result.returncode != 0:
        raise ReportError(
            '%s exited %d: %s' % (binary, result.returncode, result.stderr.strip()),
            EXIT_SESICTRL)

    return result.stdout


def parse_sesictrl_json(raw):
    """Extracts per-host checkouts from sesictrl JSON output.

    This is the only site-specific part of the script. It is written against the
    shape sesictrl emits for ``print-license --format json --show-all``: a list
    of license records, each naming a product and carrying a list of the machines
    currently using it. Both the top-level container and the per-record key names
    vary between Houdini versions, so several spellings are accepted, as does
    where a machine's ``user@host`` identity lands; ``split_identity`` untangles
    that.

    Replace the body wholesale if your sesictrl emits something else. The
    contract is all that matters: raw output in, ``Checkout`` tuples out.

    :type  raw: str
    :param raw: stdout from sesictrl
    :rtype:  tuple[list[Checkout], dict[str, int]]
    :return: observed checkouts, and total seat counts keyed by product string
    :raises ReportError: if the output is not parseable JSON in a known shape
    """
    try:
        document = json.loads(raw)
    except ValueError as exc:
        raise ReportError('sesictrl output is not valid JSON: %s' % exc, EXIT_PARSE)

    # The license list is either the document itself or nested under one of a
    # few keys depending on version.
    records = None
    if isinstance(document, list):
        records = document
    elif isinstance(document, dict):
        for key in ('licenses', 'license_list', 'keys', 'results'):
            if isinstance(document.get(key), list):
                records = document[key]
                break
    if records is None:
        raise ReportError(
            'could not find a license list in sesictrl output; adapt '
            'parse_sesictrl_json() to your version', EXIT_PARSE)

    checkouts = []
    totals = collections.Counter()

    for record in records:
        if not isinstance(record, dict):
            continue

        product = _first_string(record, ('product', 'product_id', 'license', 'name'))
        if not product:
            continue

        totals[product] += _first_int(record, ('count', 'total', 'quantity', 'seats'))

        for usage in _usage_entries(record):
            user, host = split_identity(
                _first_string(usage, ('host', 'hostname', 'machine', 'server')),
                _first_string(usage, ('user', 'username', 'owner')))
            if not host:
                continue
            checkouts.append(Checkout(
                product=product,
                host=host,
                user=user,
                tokens=max(1, _first_int(usage, ('count', 'tokens', 'used')) or 1)))

    if records and not totals:
        # Records were present but none named a product we recognize: this build
        # of sesictrl uses key names this parser does not know. Reporting the
        # empty result would replace (clear) every external hold, so fail closed.
        raise ReportError(
            'no recognizable license records in sesictrl output; adapt '
            'parse_sesictrl_json() to your version', EXIT_PARSE)

    logger.debug('parsed %d checkouts across %d products',
                 len(checkouts), len(totals))
    return checkouts, dict(totals)


def _usage_entries(record):
    """Yields the per-machine usage entries from one license record.

    Entries are dicts in most versions, but some list bare ``user@host``
    identities instead; those are wrapped so callers see one shape.
    """
    for key in ('users', 'usage', 'in_use', 'checkouts', 'clients'):
        entries = record.get(key)
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    yield entry
                elif isinstance(entry, str) and entry.strip():
                    yield {'user': entry}
            return
        # Some versions report a single host per record rather than a list.
        if isinstance(entries, dict):
            yield entries
            return
    # Fall back to a flat record that names its own host.
    if any(k in record for k in ('host', 'hostname', 'machine')):
        yield record


def _first_string(mapping, keys):
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


def _first_int(mapping, keys):
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value)
    return 0


def load_config(path):
    """Loads and validates the product-to-limit mapping.

    :type  path: str
    :param path: path to the YAML config
    :rtype:  dict
    :return: parsed config
    :raises ReportError: if the config is missing or malformed
    """
    try:
        with open(path, 'r') as handle:
            config = yaml.safe_load(handle)
    except (IOError, OSError) as exc:
        raise ReportError('cannot read config %s: %s' % (path, exc), EXIT_CONFIG)
    except yaml.YAMLError as exc:
        raise ReportError('config %s is not valid YAML: %s' % (path, exc), EXIT_CONFIG)

    if not isinstance(config, dict) or not isinstance(config.get('limits'), dict):
        raise ReportError(
            'config %s must define a "limits" mapping' % path, EXIT_CONFIG)

    for key, entry in config['limits'].items():
        if not isinstance(entry, dict):
            raise ReportError('limits.%s must be a mapping' % key, EXIT_CONFIG)
        for required in ('product', 'limit'):
            if not entry.get(required):
                raise ReportError(
                    'limits.%s is missing "%s"' % (key, required), EXIT_CONFIG)

    return config


def build_reports(config, checkouts, totals, capture_time):
    """Maps observed checkouts onto configured Cuebot limits.

    A host holding several tokens of the same product is collapsed to the
    highest count seen, not the sum, so a machine that appears twice in the
    license server's output does not double-count.

    :type  config: dict
    :param config: parsed config
    :type  checkouts: list[Checkout]
    :param checkouts: observed checkouts
    :type  totals: dict[str, int]
    :param totals: total seat counts keyed by product string
    :type  capture_time: int
    :param capture_time: epoch seconds the license server view was captured
    :rtype:  list[limit_pb2.LimitReport]
    :return: one report per configured limit, including limits with no checkouts
    """
    reports = []

    for key, entry in sorted(config['limits'].items()):
        needle = entry['product'].lower()
        matched = [c for c in checkouts if needle in c.product.lower()]

        per_host = {}
        users = {}
        for checkout in matched:
            if checkout.tokens > per_host.get(checkout.host, 0):
                per_host[checkout.host] = checkout.tokens
                users[checkout.host] = checkout.user

        total = 0
        if entry.get('sync_max_value'):
            total = sum(count for product, count in totals.items()
                        if needle in product.lower())

        report = limit_pb2.LimitReport(
            limit_name=entry['limit'],
            total_licenses=total,
            capture_time=capture_time,
            hosts=[
                limit_pb2.LimitHostUsage(
                    host_name=host, tokens=tokens, user=users.get(host, ''))
                for host, tokens in sorted(per_host.items())
            ])
        reports.append(report)

        logger.info('%s -> limit %r: %d host(s), %d token(s)%s',
                    key, entry['limit'], len(per_host), sum(per_host.values()),
                    ', %d seats' % total if total else '')

    # An empty report is meaningful: it tells Cuebot nothing is checked out.
    # An *absent* report is also meaningful: it leaves that limit untouched.
    # Both are correct here because every configured limit always gets a report.
    return reports


def post_reports(reports, source):
    """Sends the reports to Cuebot and logs the resulting limit state.

    :type  reports: list[limit_pb2.LimitReport]
    :param reports: reports to send
    :type  source: str
    :param source: reporter identity stored on each limit
    :raises ReportError: if the RPC fails
    """
    try:
        response = opencue.api.reportLimitUsage(reports, source)
    except opencue.exception.CueException as exc:
        raise ReportError('Cuebot rejected the report: %s' % exc, EXIT_CUEBOT)

    for limit in response.limits:
        logger.info('%s: %d/%d in use (%d settled, %d pending) across %d host(s)',
                    limit.name, limit.current_usage, limit.max_value,
                    limit.settled_usage, limit.pending_usage, limit.host_count)

    for name in response.unknown_limits:
        logger.warning('limit %r is configured here but does not exist in Cuebot', name)

    for skipped in response.skipped_limits:
        if skipped.reason == limit_pb2.OUT_OF_ORDER:
            # Cuebot already holds a newer snapshot than the one just sent. That is a clock
            # problem on this host, not a race, and it will repeat until the clock is fixed.
            logger.warning('limit %r was rejected as out of order; this host\'s clock is '
                           'behind the last reporter\'s', skipped.limit_name)
        else:
            # Losing the rate-limit race means another reporter got there first, which is a
            # normal outcome; the rest of the batch still applied.
            logger.info('limit %r was reported by another reporter moments ago; skipped',
                        skipped.limit_name)


def print_dry_run(reports, source):
    """Prints exactly what would be sent, without sending it."""
    print('source: %s' % source)
    if reports:
        print('capture_time: %d' % reports[0].capture_time)
    for report in reports:
        print('limit %s (total_licenses=%d)'
              % (report.limit_name, report.total_licenses))
        if not report.hosts:
            print('    <no holders — would clear external usage>')
        for host in report.hosts:
            print('    %-32s %2d  %s'
                  % (host.host_name, host.tokens, host.user or '-'))


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description='Report Houdini license usage from sesictrl to Cuebot.')
    parser.add_argument(
        '--config', default=os.environ.get('SESICTRL_LIMITS_CONFIG', DEFAULT_CONFIG),
        help='product-to-limit mapping (default: %s)' % DEFAULT_CONFIG)
    parser.add_argument(
        '--sesictrl', default=DEFAULT_SESICTRL,
        help='path to the sesictrl executable')
    parser.add_argument(
        '--sesictrl-arg', action='append', default=[], metavar='ARG',
        help='extra argument passed to sesictrl; repeatable')
    parser.add_argument(
        '--from-file', metavar='PATH',
        help='read sesictrl JSON from a file instead of running it; use this to '
             'validate the parser against a captured sample')
    parser.add_argument(
        '--timeout', type=int, default=DEFAULT_TIMEOUT,
        help='seconds to wait for sesictrl (default: %d)' % DEFAULT_TIMEOUT)
    parser.add_argument(
        '--dry-run', action='store_true',
        help='print the report instead of sending it to Cuebot')
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help='-v for info, -vv for debug')
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    logging.basicConfig(
        level={0: logging.WARNING, 1: logging.INFO}.get(args.verbose, logging.DEBUG),
        format='%(asctime)s %(levelname)-7s %(message)s')

    try:
        config = load_config(args.config)

        # Stamp the capture time *before* running sesictrl, not after. Cuebot
        # uses it as the settlement watermark: every frame booked after this
        # instant is counted as pending. Stamping late would silently discard
        # the bookings made while sesictrl was running and under-count them.
        capture_time = int(time.time())

        if args.from_file:
            try:
                with open(args.from_file, 'r') as handle:
                    raw = handle.read()
            except (OSError, UnicodeDecodeError) as exc:
                raise ReportError(
                    'cannot read capture file %s: %s' % (args.from_file, exc), EXIT_SESICTRL)
        else:
            raw = run_sesictrl(args.sesictrl, args.timeout, args.sesictrl_arg)

        checkouts, totals = parse_sesictrl_json(raw)
        reports = build_reports(config, checkouts, totals, capture_time)
        source = config.get('source', 'sesictrl')

        if args.dry_run:
            print_dry_run(reports, source)
        else:
            post_reports(reports, source)

    except ReportError as exc:
        # Deliberately bail without posting. A wrong snapshot is far worse than
        # a missing one: an empty report would clear every external hold and
        # open the license gate wide. Cuebot's report_ttl staleness handling is
        # the designed response to a reporter that has gone quiet.
        logger.error('%s — nothing reported to Cuebot', exc)
        return exc.exit_code

    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
