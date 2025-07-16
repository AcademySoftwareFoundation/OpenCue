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


"""Validator functions."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import re


def matchLettersAndNumbersOnly(value):
    """Matches strings of letters and numbers."""
    if re.match(r'^[a-zA-Z0-9]+$', value):
        return True
    return False


def matchNoSpecialCharactersOnly(value):
    """Matches strings containing letters, numbers, '.', '-','_', \t and \n"""
    if re.match(r'^[a-zA-Z0-9.\-_\s]+$', value):
        return True
    return False


def matchLettersOnly(value):
    """Matches strings container letters only."""
    if re.match(r'^[a-zA-Z]+$', value):
        return True
    return False


def matchNoSpaces(value):
    """Matches strings with no spaces."""
    if re.search(r'\s', value):
        return False
    return True


def matchNumbersOnly(value):
    """Matches strings with numbers and '.' only."""
    if re.match(r'^-?[0-9.]+$', value):
        return True
    return False


def matchIntegers(value):
    """Matches positive and negative integers."""
    if re.match(r'^-?[0-9]+$', value):
        return True
    return False


def matchPositiveIntegers(value):
    """Matches integers greater than 0."""
    if re.match(r'^[0-9]+$', value) and int(value) >= 1:
        return True
    return False


def moreThan3Chars(value):
    """String must contain at least 3 characters."""
    if len(value) >= 3:
        return True
    return False

def notEmptyString(value):
    """String must contain at least 1 character."""
    if len(value) == 0:
        return False
    return True
