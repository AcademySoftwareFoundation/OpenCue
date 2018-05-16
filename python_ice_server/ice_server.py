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



# $HeadURL$
# $LastChangedDate$
# $LastChangedBy$
# $LastChangedRevision$

import collections
import cPickle
import cStringIO
import os
import sys
import thread
import traceback
import urllib
import logging
import re
import socket
import time

import Ice
import spi.SpiIce

__all__ = ['daemonize',
           'ENABLE_ASSERTIONS',
           'ServantLocator',
           'SpiAutoPopulatedExceptionMixin',
           'SpiCauseSeq',
           'reopen_stdout_stderr',
           'throw_only']

# If assertions are enabled.
ENABLE_ASSERTIONS = True

def reopen_stdout_stderr(log_path):
    """Flush sys.stdout and sys.stderr and then reopen the underlying
    file descriptor for both stdout and stderr to the file at
    LOG_PATH.  LOG_PATH is opened before stdout and stderr are closed,
    so if LOG_PATH fails to open, stdout and stderr will remain
    unchanged."""

    log_fd = os.open(log_path, os.O_CREAT|os.O_WRONLY|os.O_TRUNC, 0644)

    for f in [sys.stdout, sys.stderr]:
        fileno = f.fileno()
        f.flush()
        os.close(fileno)
        os.dup2(log_fd, fileno)

    os.close(log_fd)

def daemonize(log_path=None, chdir_to_root=True):
    """Daemonizes the current process.  After completion, the process
    will be in a new session with stdin reading from /dev/null and
    stdout and stderr writing to /dev/null with all other file
    descriptors closed.  If CHDIR_TO_ROOT is True, then the process'
    current working directory will be changed to / after opening the
    log files; if CHDIR_TO_ROOT is false, then the current working
    directory is not changed.  If LOG_PATH is provided, then stdout
    and stderr write to LOG_PATH.  LOG_PATH may be a relative path to
    the process' current working directory before calling daemonize()."""

    import resource

    if (hasattr(os, "devnull")):
        dev_null = os.devnull
    else:
        dev_null = "/dev/null"

    if not log_path:
        log_path = dev_null

    if os.fork() != 0:
        os._exit(0)

    os.setsid()

    if os.fork() != 0:
        os._exit(0)

    os.close(sys.stdin.fileno())
    os.open(dev_null, os.O_RDONLY)

    # The log file is opened before chdir'ing so a relative path may
    # be used and is opened before stdout and stderr are closed so any
    # errors in opening it will appear on stderr.
    reopen_stdout_stderr(log_path)

    if chdir_to_root:
        os.chdir('/')

    max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if max_fd == resource.RLIM_INFINITY:
        max_fd = 1024
    for fd in range(3, max_fd+1):
        try:
            # Ice.loadSlice() function sometimes open /dev/urandom to
            # get random numbers. If daemonize() function is called after
            # Ice.loadSlice(), we should not close /dev/urandom. Or else
            # the child process will get exceptions when trying to access
            # /dev/urandom.
            fn = os.readlink("/proc/%s/%s" % (os.getpid(), fd))
            if fn != "/dev/urandom":
                os.close(fd)
        except OSError:
            pass

def ice_log(f):
    """
    A decorator that can be used for any ice method that will let it
    log the name and ip address of the remote machine.
    """
    def ice_call_with_log(*args, **kwargs):
        msg = "ICECALL:%s" % f.__name__
        cur_ctx = args[-1]
        if cur_ctx and isinstance(cur_ctx, Ice.IcePy.Current):
            m = re.match("(.*?)remote address = (?P<IPADDR>.*?):\d+",
                    cur_ctx.con.toString(), re.DOTALL)
            ipaddr = m.group('IPADDR')
            msg += " IPADDR:%s" % ipaddr
            try:
                #try to get host address
                msg += " HOST:%s" % socket.gethostbyaddr(ipaddr)[0]
            except:
                pass
        logging.info(msg)
        return f(*args, **kwargs)
    return ice_call_with_log

def ice_log_with_timing(f):
    def ice_call_with_log(*args, **kwargs):
        msg = "ICECALL:%s" % f.__name__
        cur_ctx = args[-1]
        if cur_ctx and isinstance(cur_ctx, Ice.IcePy.Current):
            m = re.match("(.*?)remote address = (?P<IPADDR>.*?):\d+",
                    cur_ctx.con.toString(), re.DOTALL)
            ipaddr = m.group('IPADDR')
            msg += " IPADDR:%s" % ipaddr
            try:
                #try to get host address
                msg += " HOST:%s" % socket.gethostbyaddr(ipaddr)[0]
            except:
                pass
        ts = time.time()
        result = f(*args, **kwargs)
        te = time.time()
        msg += " (%2.2f sec) " % (te -ts)
        logging.info(msg)
        return result
    return ice_call_with_log

class SpiAutoPopulatedExceptionMixin:
    """Mixin class for subtypes of the Ice generated SpiIce exception
    classes.  This mixin initializes the stackTrace and causedBy
    fields in the base SpiIce exception class."""

    def __init__(self, exc_info):
        """Initialize the stackTrace and causedBy fields in the base
        SpiIce exception class this mixin is mixed in with.  If the
        SpiIce exception that is being initialized should be chained
        with another exception, then exc_info should be the result of
        a sys.exc_info() call, otherwise, it should be None.

        Because the exception information from sys.exc_info() persists
        even after an exception has been handled, there is no way for
        this method to know if the information in sys.exc_info()
        should be chained into the new SpiIce exception that is
        currently being initialized, unless this mixin were to require
        that sys.exc_clear() were to be used to clear any recorded
        exception information.  However, this would place an
        additional burden on the programmer and be easily forgotten.
        So if the new SpiIce exception should chain another exception,
        then the exception information must be passed in explicitly."""

        # Populate the stackTrace field in the exception using a newly
        # generated stack trace for the construction of the SpiIce
        # exception instance.  Reverse the Python stack trace so that
        # the stack appears in the same order as the Java stack.
        frames = traceback.extract_stack()[:-2]
        self.stackTrace = ['%s:%s in %s: %s' % f for f in frames]
        self.stackTrace.reverse()

        # Populate the causedBy field if a chained exception was
        # given.
        if exc_info is not None:
            exc_type, exc, tb = exc_info

            if exc_type is not None and \
               exc is not None and \
               tb is not None:
                # A new SpiIceException should not be chained to
                # another SpiIceException, so warn the developers that
                # they should catch and handle the SpiIceException
                # separately from any other exceptions.
                if isinstance(exc, spi.SpiIce.SpiIceException):
                    # ### Log this warning.
                    pass

                frames = traceback.extract_tb(tb)
                stacktrace = ['%s:%s in %s: %s' % f for f in frames]
                stacktrace.reverse()

                message = 'Caught %s: %s' % (exc_type, str(exc))
                self.causedBy = [spi.SpiIce.SpiIceCause(message, stacktrace)]
            else:
                self.causedBy = []
        else:
            self.causedBy = []

class SpiDoesNotExistException(spi.SpiIce.SpiIceDoesNotExistException,
                               SpiAutoPopulatedExceptionMixin):
    """Subclass of SpiIceDoesNotExistException which automatically
    initializes the stackTrace and causedBy fields."""

    def __init__(self, message, exc_info=None):
        spi.SpiIce.SpiIceDoesNotExistException.__init__(self, message)
        SpiAutoPopulatedExceptionMixin.__init__(self, exc_info)

class SpiIllegalArgumentException(spi.SpiIce.SpiIceIllegalArgumentException,
                                  SpiAutoPopulatedExceptionMixin):
    """Subclass of SpiIceIllegalArgumentException which automatically
    initializes the stackTrace and causedBy fields."""

    def __init__(self, message, exc_info=None):
        spi.SpiIce.SpiIceIllegalArgumentException.__init__(self, message)
        SpiAutoPopulatedExceptionMixin.__init__(self, exc_info)

class SpiRuntimeException(spi.SpiIce.SpiIceRuntimeException,
                          SpiAutoPopulatedExceptionMixin):
    """Subclass of SpiIceRuntimeException which automatically
    initializes the stackTrace and causedBy fields."""

    def __init__(self, message, exc_info=None):
        spi.SpiIce.SpiIceRuntimeException.__init__(self, message)
        SpiAutoPopulatedExceptionMixin.__init__(self, exc_info)

class SpiCauseSeq(list):
    """Subclass of list that provides a constructor that takes an
    instance of a class that mixes in SpiAutoPopulatedExceptionMixin
    exception.  It populates the list with the exception to have a
    list of SpiIceCause's."""

    def __init__(self, e):
        list.__init__(self)
        self.append(spi.SpiIce.SpiIceCause(e.message, e.stackTrace))
        self.extend(e.causedBy)

def throw_only(exception_class, message_lambda):
    """Decorate a function or method to only throw SpiIceException's.
    If a non-SpiIceException is caught, it is chained into a new
    EXCEPTION_CLASS exception with a message generated by executing
    MESSAGE_LAMBDA with the arguments to the decorated function.  This
    allows custom exception messages to be generated using the fields
    from the 'self' object and the arguments to the function.  The
    EXCEPTION_CLASS constructor should accept two arguments, the first
    is the message generated by MESSAGE_LAMBDA and the second is the
    output of sys.exc_info()."""

    def decorator(f):
        def new_f(*args, **kwds):
            try:
                return f(*args, **kwds)
            except spi.SpiIce.SpiIceException:
                raise
            except Exception:
                raise exception_class(message_lambda(args), sys.exc_info())
        return new_f
    return decorator

class DoublyLinkedNode(object):
    """Instances of this class are nodes in a doubly linked list and
    also contain an Ice servant and the Ice identity name that the
    servant was constructed from."""

    __slots__ = ['ice_id_name', 'lru_next', 'lru_prev', 'servant']

    def __init__(self, ice_id_name, servant, lru_prev, lru_next):
        self.ice_id_name = ice_id_name
        self.servant = servant
        self.lru_prev = lru_prev
        self.lru_next = lru_next

class Servants(object):
    """For a single Ice identity name, this contains a deque of
    DoublyLinkedNode's for that identity that can be used and a count
    of DoublyLinkedNode's that have been popped from the deque and are
    currently being used."""

    __slots__ = ['deque', 'in_use_count']

    def __init__(self):
        self.deque = collections.deque()
        self.in_use_count = 0

class ServantLocator(Ice.ServantLocator):
    """This servant locator is used to build all the dynamically
    generated servants in this process.  The servant locator
    constructor is given the class of servants it should construct.
    When the servant locator's locate() method is called and an unused
    servant cannot be found for the Ice identity name, it calls the
    servant's constructor with a tuple of arguments which are
    unserialized from Ice identity name that the servant locator was
    asked to find.

    Each the servant locator instance contains its own a cache of
    frequently used servants and will reuse a servant if one is
    available.  The cache is not shared between servant locator
    instances.  In addition, servant instances are not shared, even if
    two requests with the same Ice identity name are received
    simultaneously.

    This design works around the thread unsafe nature of the
    Subversion objects, so having each servant have its own copy of
    Subversion objects and each servant object is being used by only
    one thread is the safest way.

    Another implication of this design is that the cache does not
    evict all the servants for a particular Ice identity name if the
    name has not been recently used, instead, it evicts servants on a
    servant by servant basis.  So when there are many concurrent
    invocations with the same Ice identity name, there may be more
    than one servant for that Ice identity name in the cache.  When
    the popularity of that Ice identity name decreases, some of the
    servants will eventually be evicted, but if there are still
    requests, then a few servants may remain in the cache.  So the
    cache automatically handles the changes in the number of requests
    against a particular Ice identity name over time.

    There are a few structures in the cache.

    1) A doubly-linked list constructed from DoublyLinkedNode
    instances to form the LRU list.  The two ends of the linked list
    are the youngest and oldest used node.

    2) A dictionary keyed by the Ice identity name.  The dictionary
    value is a Servants instance.

    3) The Servants contain two fields, the first is a deque of
    DoublyLinkedNode's.  The DoublyLinkedNode's in the Servants' deque
    are not linked directly together, rather, they are linked to form
    the LRU list.  When a DoublyLinkedNode is needed to execute a Ice
    method in locate(), it is popped off the end of the deque and in
    finished() pushed back on the end.  The second field of the
    Servants instance is a count of the number of servants actively in
    use.  This fields prevents removal of the Servants instance from
    the dictionary if all the servants are busy.
    """

    # Magic string that identities the serialization strategy used
    # here.  Do not use a ':' character in this string.  If client
    # serializes the object's identity into a string using the Ice
    # communicator identityToString() on the result of the proxy's
    # ice_getIdentity() and then reinterprets the stringified identity
    # using the communicator's stringToProxy(), the Ice runtime will
    # raise a Ice::EndpointParseException since it'll parse the
    # characters after the ':' as an endpoint, which it isn't.
    #
    # The encoding uses the Python pickle module to serialize the
    # information and then it URL quotes it, so as an optimization,
    # place both names here in case another program needs to
    # unserialize each stage separately.
    magic_string = "URLQuoted;PythonPickle;"

    def __init__(self, servant_class, cache_size):
        """Initialize a new servant locator with the class of servants
        that should be built and the maximum number of servants to
        cache."""

        self.servant_class = servant_class
        self.cache_size = cache_size

        # A lock that serializes all access to this servant locator.
        self.lock = thread.allocate_lock()

        # An LRU cache that contains a doubly-linked list of nodes.
        # These two values store the youngest and oldest
        # DoublyLinkedNode's.
        self.lru_youngest = None
        self.lru_oldest = None

        # A dictionary keyed by the Ice identity name.  The dictionary
        # value is a Servants instance.
        self.by_id_cache = {}

        # The number of servant's cached in the servant locator.
        self.count = 0

    @staticmethod
    def encode_to_ice_id_name(info):
        """Pickle the argument and then URL encode it so it is safe to
        use as an Ice identity name."""

        # Serialize the information by pickling it and the URL quote
        # it so it is safe to use in an Ice identity name.  Finally,
        # prepend the magic string to the URL quoted result.  If the
        # serialization strategy changes, then update
        # ServantLocator.magic_string to match it.
        s = cStringIO.StringIO()
        cPickle.dump(info, s, 2)
        s.reset()
        return ServantLocator.magic_string + urllib.quote(s.read(), '')

    @staticmethod
    def decode_from_ice_id_name(ice_id_name):
        """Given encoded information from an Ice identity name, first
        URL decode and then unpickle it."""

        if not ice_id_name.startswith(ServantLocator.magic_string):
            message = "The Ice identity name '%s' does not begin with the " \
                      "magic '%s' string." % (ice_id_name,
                                              ServantLocator.magic_string)
            raise SpiIllegalArgumentException(message)

        encoded = ice_id_name[len(ServantLocator.magic_string):]

        return cPickle.load(cStringIO.StringIO(urllib.unquote(encoded)))

    def validate_(self):
        """Validate consistency of the servant locator's fields."""

        if self.lru_oldest is None:
            assert self.lru_youngest is None
        if self.lru_youngest is None:
            assert self.lru_oldest is None

        # Check the path from youngest to oldest.
        if self.lru_youngest:
            count1 = 1
            node = self.lru_youngest
            assert node.lru_prev is None

            while node.lru_next:
                node = node.lru_next
                count1 += 1
            assert node is self.lru_oldest
        else:
            count1 = 0

        # Check the path from oldest to youngest.
        if self.lru_oldest:
            count2 = 1
            node = self.lru_oldest
            assert node.lru_next is None

            while node.lru_prev:
                node = node.lru_prev
                count2 += 1
            assert node is self.lru_youngest, "%s %s" % (count1, count2)
        else:
            count2 = 0

        assert count1 == count2

        # Check that the number of servants
        in_use_count = 0
        not_in_use_count = 0
        for ice_id, servants in self.by_id_cache.iteritems():
            if not servants.deque:
                assert servants.in_use_count > 0
            in_use_count += servants.in_use_count
            not_in_use_count += len(servants.deque)

        assert not_in_use_count == count1
        assert in_use_count + not_in_use_count == self.count

    def locate(self, current):
        """Locate a servant with the input Ice identity name.  A tuple
        of the DoublyLinkedNode and Servants instances that contain
        the servant is returned."""

        ice_id_name = current.id.name

        self.lock.acquire()

        try:
            if ENABLE_ASSERTIONS:
                self.validate_()

            servants_cache_lookup = self.by_id_cache.get(ice_id_name)
            servants = servants_cache_lookup

            # If there is no cache entry, then create an empty deque
            # for the servant to be inserted into when finished() is
            # called.
            if not servants:
                servants = Servants()

            if servants.deque:
                # Pop the least recently used servant from the deque
                # and also remove the servant from the LRU.  Return
                # the Ice identity name as the cookie value for the
                # cache lookup in finished().
                node = servants.deque.pop()

                if self.lru_youngest is node:
                    self.lru_youngest = node.lru_next
                if self.lru_oldest is node:
                    self.lru_oldest = node.lru_prev

                if node.lru_prev:
                    node.lru_prev.lru_next = node.lru_next
                if node.lru_next:
                    node.lru_next.lru_prev = node.lru_prev

                node.lru_prev = None
                node.lru_next = None

                servants.in_use_count += 1

                if ENABLE_ASSERTIONS:
                    self.validate_()

                return (node.servant, (node, servants))

            try:
                constructor_args = \
                    ServantLocator.decode_from_ice_id_name(ice_id_name)
            except Exception:
                ### Log this exception.
                message = "Unable to decode '%s' " \
                          "for %s." % (ice_id_name, self.servant_class)
                raise SpiRuntimeException(message, sys.exc_info())

            # Construct the servant and handle any exceptions thrown
            # by the constructor specially.
            #
            # The Slice specification for all ice_*() have no throws
            # specifications, so the server may not throw an
            # application specific exception to the client.  If it did
            # throw an application specific exception to the client,
            # the client's Ice layer will throw an
            # Ice::UnknownUserException to the caller of the Ice
            # method.
            #
            # To avoid this problem, if an ice_*() method is being
            # called, then do not return a servant and this will cause
            # the client's Ice layer to raise an
            # Ice::UnknownUserException to the caller.
            try:
                servant = self.servant_class(constructor_args)
                node = DoublyLinkedNode(ice_id_name, servant, None, None)

                if not servants_cache_lookup:
                    self.by_id_cache[ice_id_name] = servants

                servants.in_use_count += 1
                self.count += 1

                if ENABLE_ASSERTIONS:
                    self.validate_()

                return (servant, (node, servants))
            except Ice.UserException:
                if current.operation.startswith('ice_'):
                    return None

                raise
            except Exception, e:
                if current.operation.startswith('ice_'):
                    return None

                message = "Unable to construct a servant " \
                          "for '%s' with ID '%s. Error: %s'." % (self.servant_class,
                                                                 ice_id_name, str(e))
                raise Ice.UnknownLocalException(message)
        finally:
            self.lock.release()

    def finished(self, current, servant, cookie):
        node, servants = cookie

        self.lock.acquire()

        try:
            if ENABLE_ASSERTIONS:
                assert node
                assert node.lru_prev is None
                assert node.lru_next is None
                assert servants
                assert servants.in_use_count > 0
                assert servants.deque is not None

                if self.lru_youngest is None:
                    assert self.lru_oldest is None
                else:
                    assert self.lru_oldest
                    assert self.lru_youngest.lru_prev is None

                self.validate_()

            # Add the node to the front of the LRU list.
            if self.lru_youngest is None:
                self.lru_oldest = node
            else:
                self.lru_youngest.lru_prev = node

            node.lru_next = self.lru_youngest
            self.lru_youngest = node

            # Add the node to the right side of the deque.
            servants.deque.append(node)
            servants.in_use_count -= 1

            # Check just once the validity of the internal data
            # structures.
            if ENABLE_ASSERTIONS:
                self.validate_()

            # If the number of servants in the cache is greater then
            # the maximum number of servants the servant locator
            # should cache, then remove servants until either no more
            # servants could be removed or the servant count is small
            # enough.
            prev_count = -1
            while self.count > self.cache_size and self.count != prev_count:
                prev_count = self.count
                self.evict_oldest_()

        finally:
            self.lock.release()

    def evict_oldest_(self):
        # Do not do an validity check here, all callers should do one
        # before calling this method the first time.

        node = self.lru_oldest
        if node is None:
            return

        assert self.count > 0
        assert node.lru_next is None

        # Remove the node from the LRU list.
        if node.lru_prev:
            assert node.lru_prev.lru_next is node
            node.lru_prev.lru_next = None
        else:
            assert node is self.lru_youngest
            self.lru_youngest = None

        self.lru_oldest = node.lru_prev
        node.lru_prev = None

        servants = self.by_id_cache[node.ice_id_name]
        oldest_node = servants.deque.popleft()
        assert oldest_node is node

        # For this Ice identity name, if the deque is empty and there
        # are no active servants for the Ice identity name, then
        # delete the hash key.
        if 0 == len(servants.deque) and 0 == servants.in_use_count:
            del self.by_id_cache[node.ice_id_name]

        self.count -= 1

        if ENABLE_ASSERTIONS:
            self.validate_()

    def deactivate(self, category):
        if ENABLE_ASSERTIONS:
            self.validate_()

        while self.count > 0:
            self.evict_oldest_()

    def get_number_servants(self):
        """Return the number of servants cached in the servant
        locator."""

        return self.count

