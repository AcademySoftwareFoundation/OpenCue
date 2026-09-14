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

"""Module for classes related to limits."""

from opencue_proto import limit_pb2
from opencue import Cuebot


class Limit(object):
    """This class contains the grpc implementation related to a Limit."""

    def __init__(self, limit=None):
        self.data = limit
        self.stub = Cuebot.getStub('limit')

    def create(self):
        """Creates a new Limit from the current Limit object.

        :rtype:  opencue.wrappers.limit.Limit
        :return: the newly created Limit
        """
        return Limit(self.stub.Create(
            limit_pb2.LimitCreateRequest(
                name=self.name(), max_value=self.maxValue(), type=self.limitType(),
                enforcement=self.enforcement(), soft_value=self.softValue(),
                exit_status=self.exitStatus(), delay_minutes=self.delayMinutes(),
                auto_tag=self.autoTag()),
            timeout=Cuebot.Timeout).limit)

    def delete(self):
        """Deletes the limit."""
        self.stub.Delete(limit_pb2.LimitDeleteRequest(name=self.name()), timeout=Cuebot.Timeout)

    def find(self, name):
        """Finds an existing limit by its name.

        :type  name: str
        :param name: name of limit to find
        :rtype:  opencue.wrappers.limit.Limit
        :return: the limit found by name
        """
        return Limit(
            self.stub.Find(limit_pb2.LimitFindRequest(name=name), timeout=Cuebot.Timeout).limit)

    def get(self, limit_id):
        """Returns an existing limit by its id.

        :type  limit_id: str
        :param limit_id: id of limit to find
        :rtype:  opencue.wrappers.limit.Limit
        :return: the limit found by id.
        """
        return Limit(
            self.stub.Get(limit_pb2.LimitGetRequest(id=limit_id), timeout=Cuebot.Timeout).limit)

    def rename(self, newName):
        """Renames the limit.

        :type  newName: str
        :param newName: new limit name
        """
        self.stub.Rename(limit_pb2.LimitRenameRequest(old_name=self.name(), new_name=newName),
                         timeout=Cuebot.Timeout)
        self._update()

    def setMaxValue(self, maxValue):
        """Sets the maximum value of an existing limit.

        :type  maxValue: int
        :param maxValue: new limit maximum
        """
        self.stub.SetMaxValue(
            limit_pb2.LimitSetMaxValueRequest(name=self.name(), max_value=maxValue),
            timeout=Cuebot.Timeout)
        self._update()

    def setLimitType(self, limitType):
        """Sets how the limit counts tokens: per frame or per host.

        :type  limitType: limit_pb2.LimitType
        :param limitType: FRAME counts one token per running frame; HOST counts one token
                          per distinct host. For a HOST limit the maximum is the number of
                          machines the farm may spread across.
        """
        self.stub.SetType(limit_pb2.LimitSetTypeRequest(name=self.name(), type=limitType),
                          timeout=Cuebot.Timeout)
        self._update()

    def setEnforcement(self, enforcement):
        """Sets whether the limit gates booking, only informs it, or is ignored.

        :type  enforcement: limit_pb2.LimitEnforcement
        :param enforcement: ENFORCED blocks booking; ADVISORY never blocks but still biases
                            dispatch toward hosts already holding a token; DISABLED is ignored.
        """
        self.stub.SetEnforcement(
            limit_pb2.LimitSetEnforcementRequest(name=self.name(), enforcement=enforcement),
            timeout=Cuebot.Timeout)
        self._update()

    def setSoftValue(self, softValue):
        """Sets the usage above which only hosts already holding a token may book.

        :type  softValue: int
        :param softValue: soft threshold; 0 or -1 means the same as the max value
        """
        self.stub.SetSoftValue(
            limit_pb2.LimitSetSoftValueRequest(name=self.name(), soft_value=softValue),
            timeout=Cuebot.Timeout)
        self._update()

    def setReportTtl(self, reportTtl):
        """Sets the seconds after which an external report is considered stale.

        A stale limit stops blocking and behaves as advisory. 0 disables staleness for
        internal-only limits.

        :type  reportTtl: int
        :param reportTtl: staleness threshold in seconds
        """
        self.stub.SetReportTtl(
            limit_pb2.LimitSetReportTtlRequest(name=self.name(), report_ttl=reportTtl),
            timeout=Cuebot.Timeout)
        self._update()

    def setFailureRule(self, exitStatus, delayMinutes=0, autoTag=True):
        """Sets the exit status, backoff and auto-tagging behavior in one call.

        :type  exitStatus: int
        :param exitStatus: frame exit status meaning "this license was unavailable".
                           0 clears the rule; otherwise must be > 1 and unclaimed by
                           another limit.
        :type  delayMinutes: int
        :param delayMinutes: minutes to postpone a layer whose frame reported exitStatus.
                             0 tags without ever delaying.
        :type  autoTag: bool
        :param autoTag: bind the failing frame's layer to this limit
        """
        self.stub.SetFailureRule(
            limit_pb2.LimitSetFailureRuleRequest(name=self.name(), exit_status=exitStatus,
                                                 delay_minutes=delayMinutes, auto_tag=autoTag),
            timeout=Cuebot.Timeout)
        self._update()

    def holds(self, hostName=None):
        """Returns the hosts currently holding at least one token of this limit.

        :type  hostName: str
        :param hostName: host to filter on, short name or FQDN; None returns every host
        :rtype:  list<limit_pb2.LimitHold>
        :return: current token holders
        """
        return list(self.stub.GetHolds(
            limit_pb2.LimitGetHoldsRequest(limit_name=self.name(), host_name=hostName or ''),
            timeout=Cuebot.Timeout).holds)

    def bindings(self, sources=None, layerIds=None):
        """Returns the layers bound to this limit, optionally filtered by origin.

        :type  sources: list<limit_pb2.LimitBindSource>
        :param sources: binding origins to include; None means all
        :type  layerIds: list<str>
        :param layerIds: layers to restrict the answer to; None means all layers
        :rtype:  list<limit_pb2.LimitBinding>
        :return: layers bound to this limit
        """
        return list(self.stub.GetBindings(
            limit_pb2.LimitGetBindingsRequest(limit_name=self.name(), sources=sources or [],
                                              layer_ids=layerIds or []),
            timeout=Cuebot.Timeout).bindings)

    def clearBindings(self, sources):
        """Removes bindings from this limit, scoped by origin.

        The escape hatch for a mis-set exit status. SPEC bindings are never removed.

        :type  sources: list<limit_pb2.LimitBindSource>
        :param sources: origins to remove; only AUTO and MANUAL are accepted
        :rtype:  int
        :return: number of bindings removed
        """
        return self.stub.ClearBindings(
            limit_pb2.LimitClearBindingsRequest(limit_name=self.name(), sources=sources),
            timeout=Cuebot.Timeout).removed

    def _update(self):
        """Updates the current data object from the database."""
        self.data = self.stub.Get(limit_pb2.LimitGetRequest(id=self.id()),
                                  timeout=Cuebot.Timeout).limit

    def id(self):
        """Returns the limit id.

        :rtype:  str
        :return: the limit id
        """
        return self.data.id

    def name(self):
        """Returns the limit name.

        :rtype:  str
        :return: the limit name
        """
        if hasattr(self.data, 'name'):
            return self.data.name
        return ""

    def maxValue(self):
        """Returns the limit maximum.

        :rtype: int
        :return: the limit maximum
        """
        if hasattr(self.data, 'max_value'):
            return self.data.max_value
        return -1

    def currentRunning(self):
        """Returns the current amount of the limit in use.

        Deprecated alias of :meth:`currentUsage`, kept for compatibility.

        :rtype: int
        :return: current limit usage
        """
        if hasattr(self.data, 'current_running'):
            return self.data.current_running
        return -1

    def limitType(self):
        """Returns how the limit counts tokens: per frame or per host.

        :rtype:  limit_pb2.LimitType
        :return: the limit type
        """
        return self.data.type

    def enforcement(self):
        """Returns whether the limit gates booking, only informs it, or is ignored.

        :rtype:  limit_pb2.LimitEnforcement
        :return: the enforcement mode
        """
        return self.data.enforcement

    def softValue(self):
        """Returns the usage above which only hosts already holding a token may book.

        :rtype:  int
        :return: the soft threshold; -1 means the same as the max value
        """
        return self.data.soft_value

    def currentUsage(self):
        """Returns the merged usage the dispatcher gates on: settled plus pending.

        :rtype:  int
        :return: current usage, in tokens (FRAME) or machines (HOST)
        """
        return self.data.current_usage

    def settledUsage(self):
        """Returns the usage the license server reported as of the last report.

        :rtype:  int
        :return: settled usage
        """
        return self.data.settled_usage

    def pendingUsage(self):
        """Returns the usage booked since the last report, not yet visible to the server.

        A persistently high value means the reporter is behind, not that the farm is busy.

        :rtype:  int
        :return: pending usage
        """
        return self.data.pending_usage

    def hostCount(self):
        """Returns the number of distinct hosts holding at least one token.

        :rtype:  int
        :return: distinct holder count
        """
        return self.data.host_count

    def lastReportTime(self):
        """Returns the epoch seconds of the last accepted report, 0 if never reported.

        :rtype:  int
        :return: last report time
        """
        return self.data.last_report_time

    def reportSource(self):
        """Returns the identity of the last reporter, e.g. "sesictrl@lic01".

        :rtype:  str
        :return: report source
        """
        return self.data.report_source

    def reportTtl(self):
        """Returns the seconds after which a report is stale; 0 disables staleness.

        :rtype:  int
        :return: report TTL in seconds
        """
        return self.data.report_ttl

    def isReportStale(self):
        """Returns whether the last report is older than the TTL.

        A stale limit stops blocking and behaves as advisory.

        :rtype:  bool
        :return: True when the report is stale
        """
        return self.data.report_stale

    def isBlocking(self):
        """Returns whether the limit is currently gating booking.

        False for ADVISORY and DISABLED limits and for stale ENFORCED ones.

        :rtype:  bool
        :return: True when the limit blocks booking at its thresholds
        """
        return not self.data.blocking_disabled

    def exitStatus(self):
        """Returns the frame exit status meaning "this license was unavailable".

        :rtype:  int
        :return: the claimed exit status, 0 when no failure rule is set
        """
        return self.data.exit_status

    def delayMinutes(self):
        """Returns how long a layer is postponed when a frame reports the exit status.

        :rtype:  int
        :return: backoff in minutes; 0 means tag without delaying
        """
        return self.data.delay_minutes

    def autoTag(self):
        """Returns whether failing layers are automatically bound to this limit.

        :rtype:  bool
        :return: True when auto-tagging is enabled
        """
        return self.data.auto_tag

    def specLayerCount(self):
        """Returns the number of layers bound to this limit by their job spec.

        :rtype:  int
        :return: spec-declared binding count
        """
        return self.data.spec_layer_count

    def autoLayerCount(self):
        """Returns the number of layers bound to this limit by failure discovery.

        :rtype:  int
        :return: auto-bound binding count
        """
        return self.data.auto_layer_count
