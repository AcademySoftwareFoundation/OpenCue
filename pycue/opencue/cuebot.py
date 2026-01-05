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

"""Module for communicating with the Cuebot server(s)."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import object
from random import shuffle
import abc
import time
import atexit
import logging
import os
import platform

import grpc

from opencue_proto import comment_pb2
from opencue_proto import comment_pb2_grpc
from opencue_proto import criterion_pb2
from opencue_proto import cue_pb2
from opencue_proto import cue_pb2_grpc
from opencue_proto import department_pb2
from opencue_proto import department_pb2_grpc
from opencue_proto import depend_pb2
from opencue_proto import depend_pb2_grpc
from opencue_proto import facility_pb2
from opencue_proto import facility_pb2_grpc
from opencue_proto import filter_pb2
from opencue_proto import filter_pb2_grpc
from opencue_proto import host_pb2
from opencue_proto import host_pb2_grpc
from opencue_proto import job_pb2
from opencue_proto import job_pb2_grpc
from opencue_proto import limit_pb2
from opencue_proto import limit_pb2_grpc
from opencue_proto import renderPartition_pb2
from opencue_proto import renderPartition_pb2_grpc
from opencue_proto import service_pb2
from opencue_proto import service_pb2_grpc
from opencue_proto import show_pb2
from opencue_proto import show_pb2_grpc
from opencue_proto import subscription_pb2
from opencue_proto import subscription_pb2_grpc
from opencue_proto import task_pb2
from opencue_proto import task_pb2_grpc
from opencue_proto import monitoring_pb2
from opencue_proto import monitoring_pb2_grpc
from opencue.exception import ConnectionException
from opencue.exception import CueException
import opencue.config


__all__ = ["Cuebot"]

logger = logging.getLogger("opencue")


DEFAULT_MAX_MESSAGE_BYTES = 1024 ** 2 * 10
DEFAULT_GRPC_PORT = 8443

# gRPC keepalive settings to prevent "Connection reset by peer" errors
# These settings help maintain long-lived connections through load balancers and firewalls
DEFAULT_KEEPALIVE_TIME_MS = 30000  # Send keepalive ping every 30 seconds
DEFAULT_KEEPALIVE_TIMEOUT_MS = 10000  # Wait 10 seconds for keepalive response
DEFAULT_KEEPALIVE_PERMIT_WITHOUT_CALLS = True  # Send keepalive even when no active RPCs
DEFAULT_MAX_CONNECTION_IDLE_MS = 0  # Disable max idle time (keep connection open)
DEFAULT_MAX_CONNECTION_AGE_MS = 0  # Disable max connection age

if platform.system() != 'Darwin':
    # Avoid spamming users with epoll fork warning messages
    os.environ["GRPC_POLL_STRATEGY"] = "epoll1"

class Cuebot(object):
    """Used to manage the connection to the Cuebot.  Normally the connection
       to the Cuebot is made automatically as needed so you don't have to explicitly
       call Cuebot.connect().

       If you need to change the host(s) in which the library is connecting to,
       you have a couple options.  You can set it programmatically with
       Cuebot.setHosts or set the CUEBOT_HOSTS environment variable
       to a comma delimited list of host names."""
    RpcChannel = None
    Hosts = []
    Stubs = {}
    Config = opencue.config.load_config_from_file()
    Timeout = Config.get('cuebot.timeout', 10000)

    # Connection health tracking
    _lastSuccessfulCall = 0
    _consecutiveFailures = 0
    _maxConsecutiveFailures = 3  # Reset channel after this many failures
    _channelResetInProgress = False

    PROTO_MAP = {
        'action': filter_pb2,
        'allocation': facility_pb2,
        'comment': comment_pb2,
        'criterion': criterion_pb2,
        'cue': cue_pb2,
        'department': department_pb2,
        'depend': depend_pb2,
        'facility': facility_pb2,
        'filter': filter_pb2,
        'frame': job_pb2,
        'group': job_pb2,
        'host': host_pb2,
        'job': job_pb2,
        'layer': job_pb2,
        'limit': limit_pb2,
        'matcher': filter_pb2,
        'monitoring': monitoring_pb2,
        'owner': host_pb2,
        'proc': host_pb2,
        'renderPartition': renderPartition_pb2,
        'service': service_pb2,
        'show': show_pb2,
        'subscription': subscription_pb2,
        'task': task_pb2
    }

    SERVICE_MAP = {
        'action': filter_pb2_grpc.ActionInterfaceStub,
        'allocation': facility_pb2_grpc.AllocationInterfaceStub,
        'comment': comment_pb2_grpc.CommentInterfaceStub,
        'cue': cue_pb2_grpc.CueInterfaceStub,
        'depend': depend_pb2_grpc.DependInterfaceStub,
        'department': department_pb2_grpc.DepartmentInterfaceStub,
        'facility': facility_pb2_grpc.FacilityInterfaceStub,
        'filter': filter_pb2_grpc.FilterInterfaceStub,
        'frame': job_pb2_grpc.FrameInterfaceStub,
        'group': job_pb2_grpc.GroupInterfaceStub,
        'host': host_pb2_grpc.HostInterfaceStub,
        'job': job_pb2_grpc.JobInterfaceStub,
        'layer': job_pb2_grpc.LayerInterfaceStub,
        'limit': limit_pb2_grpc.LimitInterfaceStub,
        'matcher': filter_pb2_grpc.MatcherInterfaceStub,
        'monitoring': monitoring_pb2_grpc.MonitoringInterfaceStub,
        'owner': host_pb2_grpc.OwnerInterfaceStub,
        'proc': host_pb2_grpc.ProcInterfaceStub,
        'renderPartition': renderPartition_pb2_grpc.RenderPartitionInterfaceStub,
        'service': service_pb2_grpc.ServiceInterfaceStub,
        'serviceOverride': service_pb2_grpc.ServiceOverrideInterfaceStub,
        'show': show_pb2_grpc.ShowInterfaceStub,
        'subscription': subscription_pb2_grpc.SubscriptionInterfaceStub,
        'task': task_pb2_grpc.TaskInterfaceStub
    }

    @staticmethod
    def init(config=None):
        """Main init method for setting up the Cuebot object.
        Sets the communication channel and hosts.

        :type config: dict
        :param config: config dictionary, this will override the config read from disk
        """
        hosts_env = os.getenv("CUEBOT_HOSTS")

        if config:
            Cuebot.Config = config
            Cuebot.Timeout = config.get('cuebot.timeout', Cuebot.Timeout)
        if hosts_env:
            Cuebot.setHosts(hosts_env.split(","))
        else:
            facility = os.getenv("CUEBOT_FACILITY", Cuebot.Config.get("cuebot.facility_default"))
            Cuebot.setHostWithFacility(facility)
        if Cuebot.Hosts is None:
            raise CueException('Cuebot host not set. Please ensure CUEBOT_HOSTS is set ' +
                               'or a facility_default host is set in the yaml pycue config.')

    @staticmethod
    def setChannel():
        """Sets the gRPC channel connection"""
        # gRPC must specify a single host. Randomize host list to balance load across cuebots.
        hosts = list(Cuebot.Hosts)
        shuffle(hosts)
        maxMessageBytes = Cuebot.Config.get('cuebot.max_message_bytes', DEFAULT_MAX_MESSAGE_BYTES)

        # create interceptors
        interceptors = (
            RetryOnRpcErrorClientInterceptor(
                max_attempts=4,
                sleeping_policy=ExponentialBackoff(init_backoff_ms=100,
                                                   max_backoff_ms=1600,
                                                   multiplier=2),
                status_for_retry=(grpc.StatusCode.UNAVAILABLE,),
            ),
        )

        connectStr = "Not Defined"
        for host in hosts:
            if ':' in host:
                connectStr = host
            else:
                connectStr = '%s:%s' % (
                    host, Cuebot.Config.get('cuebot.grpc_port', DEFAULT_GRPC_PORT))
            # pylint: disable=logging-not-lazy
            logger.debug('connecting to gRPC at %s' % connectStr)
            # pylint: enable=logging-not-lazy
            # TODO(bcipriano) Configure gRPC TLS. (Issue #150)
            try:
                # Configure keepalive settings to prevent "Connection reset by peer" errors
                # These are essential for long-lived connections through load balancers
                keepalive_time_ms = Cuebot.Config.get(
                    'cuebot.keepalive_time_ms', DEFAULT_KEEPALIVE_TIME_MS)
                keepalive_timeout_ms = Cuebot.Config.get(
                    'cuebot.keepalive_timeout_ms', DEFAULT_KEEPALIVE_TIMEOUT_MS)
                keepalive_permit_without_calls = Cuebot.Config.get(
                    'cuebot.keepalive_permit_without_calls', DEFAULT_KEEPALIVE_PERMIT_WITHOUT_CALLS)

                channel_options = [
                    ('grpc.max_send_message_length', maxMessageBytes),
                    ('grpc.max_receive_message_length', maxMessageBytes),
                    # Keepalive settings to maintain connection health
                    ('grpc.keepalive_time_ms', keepalive_time_ms),
                    ('grpc.keepalive_timeout_ms', keepalive_timeout_ms),
                    ('grpc.keepalive_permit_without_calls', keepalive_permit_without_calls),
                    # Allow client to send keepalive pings even without data
                    ('grpc.http2.max_pings_without_data', 0),
                    # Minimum time between pings (allows more frequent pings)
                    ('grpc.http2.min_time_between_pings_ms', 10000),
                    # Don't limit ping strikes (server may reject too many pings)
                    ('grpc.http2.min_ping_interval_without_data_ms', 5000),
                ]

                Cuebot.RpcChannel = grpc.intercept_channel(
                    grpc.insecure_channel(connectStr, options=channel_options),
                    *interceptors)
                # Test the connection
                Cuebot.getStub('cue').GetSystemStats(
                    cue_pb2.CueGetSystemStatsRequest(), timeout=Cuebot.Timeout)
            # pylint: disable=broad-except
            except Exception:
                logger.warning('Could not establish grpc channel with %s', connectStr)
                continue
            atexit.register(Cuebot.closeChannel)
            return None
        raise ConnectionException('No grpc connection could be established. ' +
                                  'Please check configured cuebot hosts: ' + connectStr)

    @staticmethod
    def closeChannel():
        """Close the gRPC channel, delete it and reset it to None."""
        if Cuebot and Cuebot.RpcChannel is not None:
            Cuebot.RpcChannel.close()
            del Cuebot.RpcChannel
            Cuebot.RpcChannel = None

    @staticmethod
    def resetChannel():
        """Close and reopen the gRPC channel."""
        Cuebot.closeChannel()
        Cuebot.setChannel()

    @staticmethod
    def setHostWithFacility(facility):
        """Sets hosts to connect to based on the provided facility.
        If an unknown facility is provided, it will fall back to the one listed
        in cuebot.facility_default

        :type  facility: str
        :param facility: a facility named in the config file"""
        if facility not in list(Cuebot.Config.get("cuebot.facility").keys()):
            default = Cuebot.Config.get("cuebot.facility_default")
            logger.warning("The facility '%s' does not exist, defaulting to %s", facility, default)
            facility = default
        logger.debug("setting facility to: %s", facility)
        hosts = Cuebot.Config.get("cuebot.facility")[facility]
        Cuebot.setHosts(hosts)

    @staticmethod
    def setHosts(hosts):
        """Sets the cuebot host names to connect to.

        :param hosts: a list of hosts or a host
        :type hosts: list<str> or str"""
        if isinstance(hosts, str):
            hosts = [hosts]
        logger.debug("setting new server hosts to: %s", hosts)
        Cuebot.Hosts = hosts
        Cuebot.resetChannel()

    @staticmethod
    def setTimeout(timeout):
        """Sets the default network timeout.

        :param timeout: The network connection timeout in millis.
        :type timeout: int
        """
        logger.debug("setting new server timeout to: %d", timeout)
        Cuebot.Timeout = timeout

    @classmethod
    def getProto(cls, name):
        """Returns a proto class for the given name."""
        proto = cls.PROTO_MAP.get(name)
        if proto is None:
            raise ValueError("Could not find proto for {}.".format(name))
        return proto

    @classmethod
    def getService(cls, name):
        """Returns the service for the given name."""
        service = cls.SERVICE_MAP.get(name)
        if service is None:
            raise ValueError("Could not find stub interface for {}.".format(name))
        return service

    @classmethod
    def getStub(cls, name):
        """Get the matching stub from the SERVICE_MAP.
        Reuse an existing one if possible.

        :param name: name of stub key for SERVICE_MAP
        :type name: str"""
        if Cuebot.RpcChannel is None:
            cls.init()

        service = cls.getService(name)
        return service(Cuebot.RpcChannel)

    @staticmethod
    def getConfig():
        """Gets the Cuebot config object, originally read in from the config file on disk."""
        return Cuebot.Config

    @staticmethod
    def recordSuccessfulCall():
        """Record a successful gRPC call to track connection health."""
        Cuebot._lastSuccessfulCall = time.time()
        Cuebot._consecutiveFailures = 0

    @staticmethod
    def recordFailedCall():
        """Record a failed gRPC call and trigger channel reset if needed.

        Returns True if the channel was reset and the caller should retry."""
        Cuebot._consecutiveFailures += 1

        if Cuebot._consecutiveFailures >= Cuebot._maxConsecutiveFailures:
            if not Cuebot._channelResetInProgress:
                Cuebot._channelResetInProgress = True
                try:
                    logger.warning(
                        "Connection appears unhealthy after %d consecutive failures, "
                        "resetting gRPC channel...", Cuebot._consecutiveFailures)
                    Cuebot.resetChannel()
                    Cuebot._consecutiveFailures = 0
                    return True
                except Exception as e:
                    logger.error("Failed to reset gRPC channel: %s", e)
                finally:
                    Cuebot._channelResetInProgress = False
        return False

    @staticmethod
    def checkChannelHealth():
        """Check if the gRPC channel is healthy by making a simple call.

        Returns True if healthy, False otherwise."""
        if Cuebot.RpcChannel is None:
            return False

        try:
            Cuebot.getStub('cue').GetSystemStats(
                cue_pb2.CueGetSystemStatsRequest(), timeout=5000)
            Cuebot.recordSuccessfulCall()
            return True
        except grpc.RpcError as e:
            # pylint: disable=no-member
            if hasattr(e, 'code') and e.code() == grpc.StatusCode.UNAVAILABLE:
                details = e.details() if hasattr(e, 'details') else str(e)
                logger.warning("Channel health check failed: %s", details)
                Cuebot.recordFailedCall()
                return False
            # pylint: enable=no-member
            # Other errors might be OK (e.g., permission issues)
            return True
        except Exception as e:
            logger.warning("Channel health check failed with unexpected error: %s", e)
            return False


# Python 2/3 compatible implementation of ABC
ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})


class SleepingPolicy(ABC):
    """
    Implement policy for sleeping between API retries
    """
    @abc.abstractmethod
    def sleep(self, attempt):
        """
        How long to sleep in milliseconds.
        :param attempt: the number of attempt (starting from zero)
        """
        assert attempt >= 0


class ExponentialBackoff(SleepingPolicy):
    """
    Implement policy that will increase retry period by exponentially in every try
    """
    def __init__(self,
                 init_backoff_ms,
                 max_backoff_ms,
                 multiplier=2):
        """
        inputs in ms
        """
        self._init_backoff = init_backoff_ms
        self._max_backoff = max_backoff_ms
        self._multiplier = multiplier

    def sleep(self, attempt):
        sleep_time_ms = min(
            self._init_backoff * self._multiplier ** attempt,
            self._max_backoff
        )
        time.sleep(sleep_time_ms / 1000.0)


class RetryOnRpcErrorClientInterceptor(
    grpc.UnaryUnaryClientInterceptor,
    grpc.StreamUnaryClientInterceptor
):
    """
    Implement Client/Stream interceptors for GRPC channels to retry
    calls that failed with retry-able states. This is required for
    handling server interruptions that are not automatically handled
    by grpc.insecure_channel
    """
    def __init__(self,
                 max_attempts,
                 sleeping_policy,
                 status_for_retry=None):
        self._max_attempts = max_attempts
        self._sleeping_policy = sleeping_policy
        self._retry_statuses = status_for_retry

    # pylint: disable=inconsistent-return-statements
    def _intercept_call(self, continuation, client_call_details,
                        request_or_iterator):
        for attempt in range(self._max_attempts):
            try:
                return continuation(client_call_details,
                                    request_or_iterator)
            except grpc.RpcError as response:
                # Return if it was last attempt
                if attempt == (self._max_attempts - 1):
                    return response

                # If status code is not in retryable status codes
                # pylint: disable=no-member
                if self._retry_statuses \
                        and hasattr(response, 'code') \
                        and response.code() \
                        not in self._retry_statuses:
                    return response

                self._sleeping_policy.sleep(attempt)

    def intercept_unary_unary(self, continuation, client_call_details,
                              request):
        return self._intercept_call(continuation, client_call_details,
                                    request)

    def intercept_stream_unary(
            self, continuation, client_call_details, request_iterator
    ):
        return self._intercept_call(continuation, client_call_details,
                                    request_iterator)
