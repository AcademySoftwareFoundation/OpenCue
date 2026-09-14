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

"""Tests for the sesictrl reference reporter.

Run from this directory::

    pytest test_sesictrl_report.py
"""

from __future__ import absolute_import
from __future__ import print_function

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sesictrl_report  # pylint: disable=wrong-import-position


class TestNormalizeHost:

    @pytest.mark.parametrize('reported,expected', [
        ('wkst123', 'wkst123'),
        ('WKST123.example.com', 'wkst123'),
        ('  wkst123  ', 'wkst123'),
        # sesinetd reports the account holding the license alongside the machine.
        ('dtavares@wkst123', 'wkst123'),
        ('dtavares@WKST123.example.com', 'wkst123'),
        ('', ''),
        (None, ''),
    ])
    def test_reduces_to_join_key(self, reported, expected):
        assert sesictrl_report.normalize_host(reported) == expected


class TestSplitIdentity:

    def test_splits_composite_host_field(self):
        assert sesictrl_report.split_identity('dtavares@wkst123.example.com') == (
            'dtavares', 'wkst123')

    def test_keeps_separate_fields_apart(self):
        assert sesictrl_report.split_identity('wkst123', 'dtavares') == (
            'dtavares', 'wkst123')

    def test_reads_host_from_user_field_alone(self):
        assert sesictrl_report.split_identity('', 'dtavares@wkst123') == (
            'dtavares', 'wkst123')

    def test_plain_user_field_is_not_mistaken_for_a_host(self):
        assert sesictrl_report.split_identity('', 'dtavares') == ('dtavares', '')

    def test_named_user_wins_over_the_composite(self):
        assert sesictrl_report.split_identity('root@wkst123', 'dtavares') == (
            'dtavares', 'wkst123')


class TestParseSesictrlJson:

    def test_composite_host_field(self):
        raw = json.dumps([{
            'product': 'Houdini-Master',
            'count': 30,
            'users': [
                {'host': 'dtavares@wkst123.example.com', 'count': 1},
                {'host': 'ana@wkst123.example.com', 'count': 1},
            ],
        }])

        checkouts, totals = sesictrl_report.parse_sesictrl_json(raw)

        assert totals == {'Houdini-Master': 30}
        assert [(c.host, c.user) for c in checkouts] == [
            ('wkst123', 'dtavares'), ('wkst123', 'ana')]

    def test_bare_identity_strings(self):
        raw = json.dumps({'license_list': [{
            'product': 'Houdini-Escape',
            'count': 10,
            'users': ['dtavares@wkst123', 'ana@render042.example.com'],
        }]})

        checkouts, _ = sesictrl_report.parse_sesictrl_json(raw)

        assert [(c.host, c.user, c.tokens) for c in checkouts] == [
            ('wkst123', 'dtavares', 1), ('render042', 'ana', 1)]

    def test_split_host_and_user_fields(self):
        raw = json.dumps([{
            'product': 'Houdini-Master',
            'total': 30,
            'usage': [{'machine': 'render042', 'username': 'dtavares', 'tokens': 2}],
        }])

        checkouts, _ = sesictrl_report.parse_sesictrl_json(raw)

        assert [(c.host, c.user, c.tokens) for c in checkouts] == [
            ('render042', 'dtavares', 2)]

    def test_flat_record_naming_its_own_host(self):
        raw = json.dumps([
            {'product': 'Houdini-Master', 'count': 5, 'host': 'dtavares@render042'}])

        checkouts, _ = sesictrl_report.parse_sesictrl_json(raw)

        assert [(c.host, c.user) for c in checkouts] == [('render042', 'dtavares')]

    def test_unusable_hosts_are_dropped(self):
        raw = json.dumps([{
            'product': 'Houdini-Master',
            'count': 5,
            'users': [{'user': 'dtavares'}, {'host': 'render042'}],
        }])

        checkouts, _ = sesictrl_report.parse_sesictrl_json(raw)

        assert [c.host for c in checkouts] == ['render042']

    def test_unrecognized_records_fail_closed(self):
        raw = json.dumps([{'sku': 'Houdini-Master', 'seats_used': 3}])

        with pytest.raises(sesictrl_report.ReportError) as exc:
            sesictrl_report.parse_sesictrl_json(raw)

        assert exc.value.exit_code == sesictrl_report.EXIT_PARSE

    def test_invalid_json_fails_closed(self):
        with pytest.raises(sesictrl_report.ReportError) as exc:
            sesictrl_report.parse_sesictrl_json('not json')

        assert exc.value.exit_code == sesictrl_report.EXIT_PARSE


class TestBuildReports:

    CONFIG = {'limits': {'houdini': {'product': 'Houdini', 'limit': 'houdini'}}}

    def test_one_machine_counts_once(self):
        """Two artists on one machine hold one Houdini license, not two."""
        checkouts = [
            sesictrl_report.Checkout('Houdini-Master', 'wkst123', 'dtavares', 1),
            sesictrl_report.Checkout('Houdini-Master', 'wkst123', 'ana', 1),
        ]

        reports = sesictrl_report.build_reports(
            self.CONFIG, checkouts, {'Houdini-Master': 30}, 1000)

        assert len(reports) == 1
        assert [(h.host_name, h.tokens) for h in reports[0].hosts] == [('wkst123', 1)]

    def test_sync_max_value_off_by_default(self):
        reports = sesictrl_report.build_reports(
            self.CONFIG, [], {'Houdini-Master': 30}, 1000)

        assert reports[0].total_licenses == 0
        assert reports[0].capture_time == 1000
