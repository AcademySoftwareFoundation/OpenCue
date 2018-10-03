#  Copyright (c) 2018 Sony Pictures Imageworks Inc.
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



"""
Project: Cue3 Library

Module: Cuebot.py - Cue3 Library API.

Created: February 16, 2008

Contact: Middle-Tier Group

SVN: $Id$
"""
import grpc
import os
import sys
import pwd
import socket
import logging
import yaml
import atexit

import Ice
import cue.CueClientIce as CueClientIce

from exception import CuebotProxyCreationError

__all__ = ["Cuebot"]

logger = logging.getLogger("cue3")

# check for facility specific configurations.
fcnf = os.environ.get('CUE3_CONF', '')

if os.path.exists(fcnf):
    config = yaml.load(open(fcnf).read())
else:
    _this_dir = os.path.dirname(__file__)
    default_config = os.path.join(os.path.dirname(_this_dir), 'etc/default.yaml')
    config = yaml.load(open(default_config).read())

def _buildProxyString(hosts, interface, timeout=0):
    """Returns a proxy to an interface on the supplied hosts
    @type  hosts: list<str>
    @param hosts: A list of hosts, port may be specified by appending ":PORT"
    @type  interface: str
    @param interface: The name of the interface
    @rtype:  str
    @return: The resulting proxy string"""
    result = []
    logger.debug("attempting to create proxy string to %s on %s" % (interface, hosts))
    result.append(interface)
    for host in hosts:
        try:
            host, port = host.split(":")
        except:
            port = "9019"
        result.append(":")
        result.append("tcp")
        result.append(" -h ")
        result.append(host)
        result.append(" -p ")
        result.append(port)
        if timeout:
            result.append(" -t %d" % timeout)
    proxyString = "".join(result)
    logger.debug("created proxy string: " + proxyString)
    return proxyString

class ObjectFactory(Ice.ObjectFactory):
    def __init__(self,class_type):
        self.__type = class_type
    def create(self, type):
        return self.__type()
    def destroy(self):
        # Nothing to do
        pass

class Cuebot:
    """Used to manage the conncection to the cuebot.  Normally the connection
       to the cuebot is made automatically as needed so you don't have to explicitly
       call Cuebot.connect().

       If you need to change the host(s) in which the library is connecting to,
       you have a couple options.  You can set it programmatically with
       Cuebot.setHosts or set the CUEBOT_HOSTS environement varaible
       to a comma delimited list of host names."""

    Hosts = []
    Proxy = None
    Communicator = None
    CueClientIce = None
    RpcChannel = None

    # The default connection timeout in milliseconds
    Timeout = config.get('cuebot.timeout', 10000)

    @staticmethod
    def init():
        """Initialize the communicator."""
        init_data = Ice.InitializationData()
        props = init_data.properties = Ice.createProperties()
        ice_init = config.get('ice.init')
        if ice_init:
            for k,v in config.get("ice.init").iteritems():
                if k == 'Ice.ACM.Client' and Ice.intVersion() >= 30600:
                    k = 'Ice.ACM.Client.Timeout'
                logger.debug("setting ice property %s %s" % (k,v))
                props.setProperty(k,str(v))

        # Allows use of implicit_context
        props.setProperty('Ice.ImplicitContext', 'Shared')

        # Allow Ice 3.5 clients, remove when server is also Ice 3.5
        if Ice.intVersion() >= 30500:
            props.setProperty('Ice.Default.EncodingVersion', '1.0')

        Cuebot.Communicator = Ice.initialize(init_data)

        def destroy():
            Cuebot.Communicator.destroy()
        atexit.register(destroy)

        # Register in the implicit context the key/value pairs for this client
        implicit_context = Cuebot.Communicator.getImplicitContext()
        implicit_context.put('argv', sys.argv[0])
        implicit_context.put('hostname', str(socket.gethostname()))
        implicit_context.put('pid', str(os.getpid()))
        implicit_context.put('username', os.getenv("USER"))

        ## Gets populated by the the enviorment, if that fails we go to config
        if os.getenv("CUEBOT_HOSTS"):
            Cuebot.setHosts(os.getenv("CUEBOT_HOSTS").split(","))
        else:
            facility_default = config.get("cuebot.facility_default")
            Cuebot.setFacility(facility_default)

    @staticmethod
    def setHosts(hosts):
        """Sets the cuebot host names to connect to.
        @param hosts: a list of hosts or a host
        @type hosts: list<str> or str"""
        if isinstance(hosts, str):
            hosts = [hosts]
        logger.debug("setting new server hosts to: %s" % hosts)
        Cuebot.Hosts = hosts
        Cuebot.Proxy = Cuebot.buildProxy("CueStatic")
        Cuebot.RpcChannel = Cuebot.buildRpcChannel()

    @staticmethod
    def setTimeout(timeout):
        """Sets the default network timeout.
        @param timeout: The network connection timeout in millis.
        @type timeout: int
        """
        logger.debug("setting new server timeout to: %d" % timeout)
        Cuebot.Timeout =  timeout
        Cuebot.Proxy = Cuebot.buildProxy("CueStatic")

    @staticmethod
    def setFacility(facility):
        """Sets the facility to connect to. If an unknown facility is provided,
        it will fall back to the one listed in cuebot.facility_default
        @type  facility: str
        @param facility: a facility named in the config file"""
        if facility not in config.get("cuebot.facility").keys():
            default = config.get("cuebot.facility_default")
            logger.warning("The facility '%s' does not exist, defaulting to %s"%
                         (facility, default))
            facility = default
        logger.debug("setting facility to: %s" % facility)
        hosts = config.get("cuebot.facility")[facility]
        Cuebot.setHosts(hosts)

    @staticmethod
    def buildProxy(interface_name, proxy_name=None, timeout=0):
        """Creates and returns a cuebot whiteboard proxy. The proxy is unchecked
        To build a job proxy you would use:
        buildProxy("JobInterface", "manageJob/%s" % id)
        @type  interface_name: str
        @param interface_name: The name of the interface
        @type  proxy_name: str
        @param proxy_name: (optional) The proxy name
        @type timeout: int
        @param timeout: the time out in milliseconds. If no timeout is set then
                        the defualt timeout stored in Cuebot.Timeout is used.
        @rtype:  Ice.Proxy
        @return: The created proxy"""
        prx_str = "Error, Not Created"
        try:
            prx_str = _buildProxyString(Cuebot.Hosts, proxy_name or interface_name,
                                        timeout or Cuebot.Timeout)
            prx_obj = Cuebot.Communicator.stringToProxy(prx_str)
            return getattr(CueClientIce,"%sPrx" % interface_name).uncheckedCast(prx_obj)
        except Exception,e:
            ## catch this and send it up with the interface and proxy
            ## string we were using.
            raise CuebotProxyCreationError("failed to connect to cuebot interface "  +
                                           interface_name + " on proxy: " + prx_str, e)

    @staticmethod
    def buildRpcChannel():
        # gRPC must specify a single host.
        hostname = Cuebot.Hosts[0].split(':')[0]
        connect_str = '%s:%s' % (hostname, config.get('cuebot.grpc_port', 8443))
        logger.debug('connecting to gRPC at %s', connect_str)
        # TODO(cipriano) Configure gRPC TLS.
        return grpc.insecure_channel(connect_str)

    @staticmethod
    def register(class_obj, parent_name):
        """Register a class with an ice object factory
        @type  class_obj: The class to register
        @param class_obj: paramA_description
        @type  parent_name: str
        @param parent_name: The name of the parent
        @rtype:  return_type
        @return: return_description"""
        of = ObjectFactory(class_obj)
        Cuebot.Communicator.addObjectFactory(of, parent_name)


class ObjectFactory(Ice.ObjectFactory):
    def __init__(self,class_type):
        self.__type = class_type
    def create(self, type):
        return self.__type()
    def destroy(self):
        # Nothing to do
        pass

