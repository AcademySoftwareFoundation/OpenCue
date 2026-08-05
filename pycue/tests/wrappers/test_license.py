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

"""Tests for `opencue.wrappers.license`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest

import mock

from opencue_proto import license_pb2
import opencue.api
import opencue.wrappers.license


TEST_LICENSE_NAME = 'hengine'
TEST_LICENSE_FEATURE = 'Houdini Engine'


def _license():
    return license_pb2.License(
        name=TEST_LICENSE_NAME,
        feature=TEST_LICENSE_FEATURE,
        total=800,
        available=794,
        host_based=True,
        headroom=5,
        running_frames=12,
        running_hosts=3,
        provider_host_count=2)


@mock.patch('opencue.cuebot.Cuebot.getStub')
class LicenseTests(unittest.TestCase):

    def testFind(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Find.return_value = license_pb2.LicenseFindResponse(license=_license())
        getStubMock.return_value = stubMock

        lic = opencue.wrappers.license.License().find(TEST_LICENSE_NAME)

        stubMock.Find.assert_called_with(
            license_pb2.LicenseFindRequest(name=TEST_LICENSE_NAME), timeout=mock.ANY)
        self.assertEqual(lic.name(), TEST_LICENSE_NAME)

    def testAccessors(self, getStubMock):
        getStubMock.return_value = mock.Mock()

        lic = opencue.wrappers.license.License(_license())

        self.assertEqual(lic.id(), TEST_LICENSE_NAME)
        self.assertEqual(lic.name(), TEST_LICENSE_NAME)
        self.assertEqual(lic.feature(), TEST_LICENSE_FEATURE)
        self.assertEqual(lic.total(), 800)
        self.assertEqual(lic.available(), 794)
        self.assertEqual(lic.inUse(), 6)
        self.assertTrue(lic.hostBased())
        self.assertEqual(lic.headroom(), 5)
        self.assertEqual(lic.runningFrames(), 12)
        self.assertEqual(lic.runningHosts(), 3)
        self.assertEqual(lic.providerHostCount(), 2)


@mock.patch('opencue.cuebot.Cuebot.getStub')
class LicensingStatusTests(unittest.TestCase):

    def testStatusAndLicenses(self, getStubMock):
        getStubMock.return_value = mock.Mock()

        response = license_pb2.LicenseGetAllResponse(
            source=license_pb2.LicenseSourceStatus(
                configured=True,
                provider='http://lic-reporter:9101/licenses',
                env_key='CUE_LICENSES',
                poll_seconds=20,
                stale_seconds=300,
                has_sample=True,
                age_seconds=17,
                stale=False),
            licenses=[_license()])
        status = opencue.wrappers.license.LicensingStatus(response)

        self.assertTrue(status.configured())
        self.assertEqual(status.provider(), 'http://lic-reporter:9101/licenses')
        self.assertEqual(status.envKey(), 'CUE_LICENSES')
        self.assertEqual(status.pollSeconds(), 20)
        self.assertEqual(status.staleSeconds(), 300)
        self.assertTrue(status.hasSample())
        self.assertEqual(status.ageSeconds(), 17)
        self.assertFalse(status.stale())
        self.assertEqual(len(status.licenses()), 1)
        self.assertEqual(status.licenses()[0].name(), TEST_LICENSE_NAME)

    def testEmptyStatusFailsClosed(self, getStubMock):
        getStubMock.return_value = mock.Mock()

        status = opencue.wrappers.license.LicensingStatus()

        self.assertFalse(status.configured())
        self.assertFalse(status.hasSample())
        self.assertTrue(status.stale())
        self.assertEqual(status.licenses(), [])


@mock.patch('opencue.cuebot.Cuebot.getStub')
class ApiTests(unittest.TestCase):

    def testGetLicenses(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetAll.return_value = license_pb2.LicenseGetAllResponse(
            source=license_pb2.LicenseSourceStatus(configured=True),
            licenses=[_license()])
        getStubMock.return_value = stubMock

        licenses = opencue.api.getLicenses()

        stubMock.GetAll.assert_called_with(
            license_pb2.LicenseGetAllRequest(), timeout=mock.ANY)
        self.assertEqual(len(licenses), 1)
        self.assertEqual(licenses[0].name(), TEST_LICENSE_NAME)

    def testGetLicensingStatus(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetAll.return_value = license_pb2.LicenseGetAllResponse(
            source=license_pb2.LicenseSourceStatus(configured=False, stale=True))
        getStubMock.return_value = stubMock

        status = opencue.api.getLicensingStatus()

        self.assertFalse(status.configured())
        self.assertTrue(status.stale())
        self.assertEqual(status.licenses(), [])

    def testFindLicense(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Find.return_value = license_pb2.LicenseFindResponse(license=_license())
        getStubMock.return_value = stubMock

        lic = opencue.api.findLicense(TEST_LICENSE_NAME)

        stubMock.Find.assert_called_with(
            license_pb2.LicenseFindRequest(name=TEST_LICENSE_NAME), timeout=mock.ANY)
        self.assertEqual(lic.feature(), TEST_LICENSE_FEATURE)


if __name__ == '__main__':
    unittest.main()
