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

"""Utility methods used by the wrapper classes."""

import time


# pylint: disable=redefined-builtin
def format_time(epoch, format="%m/%d %H:%M", default="--/-- --:--"):
    """Formats time using time formatting standards.

    See: https://docs.python.org/3/library/time.html

    :type  epoch: int
    :param epoch: time as an epoch
    :type  format: str
    :param format: desired format of output string
    :type  default: str
    :param default: the output if the given time is empty
    :rtype: str
    :return: string-formatted version of the given time
    """
    if not epoch:
        return default
    return time.strftime(format, time.localtime(epoch))


def dateToMMDDHHMM(sec):
    """Returns a time in the format `%m/%d %H:%M`.

    :type  sec: int
    :param sec: time as an epoch
    :rtype:  str
    :return: time in the format %m/%d %H:%M
    """
    if sec == 0:
        return "--/-- --:--"
    return time.strftime("%m/%d %H:%M", time.localtime(sec))


def __splitTime(sec):
    """Splits a timestamp into hour, minute, and second components.

    :type  sec: int
    :param sec: timestamp as an epoch
    :rtype:  tuple
    :return: (hour, min, sec)
    """
    minute, sec = divmod(sec, 60)
    hour, minute = divmod(minute, 60)
    return hour, minute, sec


def secondsToHHMMSS(sec):
    """Returns time in the format HH:MM:SS

    :rtype:  str
    :return: Time in the format HH:MM:SS"""
    return "%02d:%02d:%02d" % __splitTime(sec)


def secondsToHMMSS(sec):
    """Returns time in the format H:MM:SS

    :rtype:  str
    :return: Time in the format H:MM:SS"""
    return "%d:%02d:%02d" % __splitTime(sec)


def secondsToHHHMM(sec):
    """Returns time in the format HHH:MM

    :rtype:  str
    :return: Time in the format HHH:MM"""
    return "%03d:%02d" % __splitTime(sec)[:2]


def secondsDiffToHMMSS(secA, secB):
    """Returns time difference of arguments in the format H:MM:SS

    :type  secA: int or float
    :param secA: seconds. 0 will be replaced with current time
    :type  secB: int or float
    :param secB: seconds. 0 will be replaced with current time
    :rtype:  str
    :return: Time difference of arguments in the format H:MM:SS
    """
    if secA == 0:
        secA = time.time()
    if secB == 0:
        secB = time.time()
    return secondsToHMMSS(max(secA, secB) - min(secA, secB))


def convert_mem(kmem, unit=None):
    """Returns an amount of memory in a human-readable string.

    :type  kmem: int
    :param kmem: amount of memory in kB
    :rtype:  str
    :return: same amount of memory formatted into a human-readable string
    """
    k = 1024
    if unit == 'K' or (unit is None and kmem < k):
        return '%dK' % kmem
    if unit == 'M' or (unit is None and kmem < pow(k, 2)):
        return '%dM' % (kmem / k)
    if unit == 'G' or (unit is None and kmem < pow(k, 3)):
        return '%.01fG' % (float(kmem) / pow(k, 2))
    return str(kmem)
