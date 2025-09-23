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


"""Functions for formatting text output."""


from __future__ import absolute_import, division, print_function

import time


def formatTime(epoch, time_format="%m/%d %H:%M", default="--/-- --:--"):
    """Formats time using time formatting standards.

    See http://docs.python.org/library/time.html

    :type epoch: int
    :param epoch: epoch timestamp to be string formatted
    :type time_format: str
    :param time_format: format the output string should follow, in time.strftime format
    :type default: str
    :param default: default string to be returned in the event the timestamp is blank
    :rtype: str
    :return: formatted time string"""
    if not epoch:
        return default
    return time.strftime(time_format, time.localtime(epoch))


def findDuration(start, stop):
    """Provides a duration between two timestamps.

    If stop time is blank, current time will be used as a stand-in.

    :type start: int
    :param start: start time as an epoch
    :type stop: int
    :param stop: stop time as an epoch
    :rtype: int
    :return: duration between the two timestamps"""
    if stop < 1:
        stop = int(time.time())
    return stop - start


def formatDuration(sec):
    """Formats a duration in HH:MM:SS format.

    :type sec: int
    :param sec: duration in seconds
    :rtype: str
    :return: duration formatted in HH:MM:SS format."""

    def splitTime(seconds):
        minutes, seconds = divmod(seconds, 60)
        hour, minutes = divmod(minutes, 60)
        return hour, minutes, seconds

    return "%02d:%02d:%02d" % splitTime(sec)


def formatLongDuration(sec):
    """Formats a duration in days:hours format, preferable for very long durations.

    :type sec: int
    :param sec: duration in seconds
    :rtype: str
    :return: duration formatted in days:hours format."""

    def splitTime(seconds):
        minutes, seconds = divmod(seconds, 60)
        hour, minutes = divmod(minutes, 60)
        days, hour = divmod(hour, 24)
        return days, hour

    return "%02d:%02d" % splitTime(sec)


def formatMem(kmem, unit=None):
    """Formats an amount of memory in human-friendly format.

    :type kmem: int
    :param kmem: amount of memory in KB
    :type unit: str
    :param unit: unit to use for formatting, if blank the unit closest in size will be used
    :rtype: str
    :return: human-friendly formatted string"""
    k = 1024
    if unit == "K" or not unit and kmem < k:
        return "%dK" % kmem
    if unit == "M" or not unit and kmem < pow(k, 2):
        return "%dM" % (kmem / k)
    return "%.01fG" % (float(kmem) / pow(k, 2))


def cutoff(s, length):
    """Truncates a string after a certain number of characters.

    :type s: str
    :param s: string to be truncated
    :type length: int
    :param length: max number of characters
    :rtype: str
    :return: truncated string"""
    if len(s) < length - 2:
        return s
    return "%s.." % s[0 : length - 2]
