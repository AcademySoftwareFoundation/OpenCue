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

"""Module for classes related to application licenses.

Licenses are read-only over the wire: the numbers come from the license
server Cuebot polls (``scheduler.license.provider``), and the tuning lives
in ``opencue.properties`` on the Cuebot side.
"""

from opencue_proto import license_pb2
from opencue import Cuebot


class License(object):
    """Read-only view of one application license in Cuebot's provider sample."""

    def __init__(self, license_=None):
        self.data = license_
        self.stub = Cuebot.getStub('license')

    def find(self, name):
        """Finds a license in the current sample by its name.

        :type  name: str
        :param name: name of license to find
        :rtype:  opencue.wrappers.license.License
        :return: the license found by name
        """
        return License(
            self.stub.Find(
                license_pb2.LicenseFindRequest(name=name), timeout=Cuebot.Timeout).license)

    def id(self):
        """Returns the license name, which is its identifier.

        Licenses have no database id; the pool name is unique within the
        provider sample.

        :rtype:  str
        :return: the license name
        """
        return self.name()

    def name(self):
        """Returns the license pool name, e.g. ``hengine``.

        :rtype:  str
        :return: the license name
        """
        if hasattr(self.data, 'name'):
            return self.data.name
        return ""

    def feature(self):
        """Returns the human-readable feature name, e.g. ``Houdini Engine``.

        :rtype:  str
        :return: the feature name
        """
        if hasattr(self.data, 'feature'):
            return self.data.feature
        return ""

    def total(self):
        """Returns the total seats the license server owns.

        :rtype: int
        :return: total seat count
        """
        if hasattr(self.data, 'total'):
            return self.data.total
        return -1

    def available(self):
        """Returns the seats the license server reports free, net of every
        consumer (workstations, CI and other farms included).

        :rtype: int
        :return: available seat count
        """
        if hasattr(self.data, 'available'):
            return self.data.available
        return -1

    def inUse(self):
        """Returns the seats currently checked out anywhere, per the server.

        :rtype: int
        :return: total minus available
        """
        if hasattr(self.data, 'total'):
            return self.data.total - self.data.available
        return -1

    def hostBased(self):
        """Returns whether one seat covers a whole machine rather than one frame.

        :rtype: bool
        :return: True when the license is host-based
        """
        if hasattr(self.data, 'host_based'):
            return self.data.host_based
        return False

    def headroom(self):
        """Returns the seats deliberately withheld from the farm for
        interactive users (``scheduler.license.headroom.<name>``).

        :rtype: int
        :return: headroom seat count
        """
        if hasattr(self.data, 'headroom'):
            return self.data.headroom
        return -1

    def runningFrames(self):
        """Returns the frames currently running on this OpenCue deploy whose
        layer declares this license.

        :rtype: int
        :return: running licensed frame count
        """
        if hasattr(self.data, 'running_frames'):
            return self.data.running_frames
        return -1

    def runningHosts(self):
        """Returns the distinct hosts running those frames.

        :rtype: int
        :return: running licensed host count
        """
        if hasattr(self.data, 'running_hosts'):
            return self.data.running_hosts
        return -1

    def providerHostCount(self):
        """Returns the hosts the provider reports holding a seat (any
        consumer, not just OpenCue); 0 when the provider does not report hosts.

        :rtype: int
        :return: provider-reported host count
        """
        if hasattr(self.data, 'provider_host_count'):
            return self.data.provider_host_count
        return -1


class LicensingStatus(object):
    """Read-only state of the Cuebot license poller plus the cached licenses.

    Wraps one ``LicenseGetAllResponse``: the poller/source status and every
    license in the current sample, fetched in a single round trip.
    """

    def __init__(self, response=None):
        self.data = response.source if response is not None else None
        self.__licenses = [
            License(lic) for lic in response.licenses] if response is not None else []

    def licenses(self):
        """Returns the licenses in the current sample.

        :rtype:  list[opencue.wrappers.license.License]
        :return: licenses, sorted by name
        """
        return self.__licenses

    def configured(self):
        """Returns whether ``scheduler.license.provider`` is set on Cuebot.

        :rtype: bool
        :return: True when a provider is configured
        """
        if hasattr(self.data, 'configured'):
            return self.data.configured
        return False

    def provider(self):
        """Returns the configured provider endpoint or script.

        :rtype:  str
        :return: the provider string, empty when unconfigured
        """
        if hasattr(self.data, 'provider'):
            return self.data.provider
        return ""

    def envKey(self):
        """Returns the layer environment key that binds layers to licenses.

        :rtype:  str
        :return: the env key, e.g. ``CUE_LICENSES``
        """
        if hasattr(self.data, 'env_key'):
            return self.data.env_key
        return ""

    def pollSeconds(self):
        """Returns the provider poll cadence in seconds.

        :rtype: int
        :return: poll interval
        """
        if hasattr(self.data, 'poll_seconds'):
            return self.data.poll_seconds
        return -1

    def staleSeconds(self):
        """Returns the age past which the sample stops being actionable.

        :rtype: int
        :return: staleness threshold in seconds
        """
        if hasattr(self.data, 'stale_seconds'):
            return self.data.stale_seconds
        return -1

    def hasSample(self):
        """Returns whether a first successful poll has landed.

        :rtype: bool
        :return: True once the poller holds a sample
        """
        if hasattr(self.data, 'has_sample'):
            return self.data.has_sample
        return False

    def ageSeconds(self):
        """Returns the age of the current sample in seconds, including the
        provider's own lag; 0 when there is no sample.

        :rtype: int
        :return: sample age
        """
        if hasattr(self.data, 'age_seconds'):
            return self.data.age_seconds
        return -1

    def stale(self):
        """Returns whether the sample is missing or too old to act on;
        licensed layers are being held while this is True.

        :rtype: bool
        :return: True when stale
        """
        if hasattr(self.data, 'stale'):
            return self.data.stale
        return True
