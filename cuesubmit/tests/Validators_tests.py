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


"""Tests for cuesubmit.Validators"""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import unittest

from cuesubmit.Validators import (
                                matchLettersAndNumbersOnly,
                                matchNoSpecialCharactersOnly,
                                matchLettersOnly,
                                matchNoSpaces,
                                matchNumbersOnly,
                                matchPositiveIntegers,
                                moreThan3Chars,
                                notEmptyString,
)


class ValidatorsTests(unittest.TestCase):

    def testMatchLettersAndNumbersOnly(self):
        self.assertTrue(matchLettersAndNumbersOnly('azAZ09'))

        self.assertFalse(matchLettersAndNumbersOnly(' az AZ 09'))
        self.assertFalse(matchLettersAndNumbersOnly(''))

        self.assertRaises(TypeError, matchLettersAndNumbersOnly, None)

    def testMatchNoSpecialCharactersOnly(self):
        self.assertTrue(matchNoSpecialCharactersOnly('azAZ09._-'))
        self.assertTrue(matchNoSpecialCharactersOnly('_-'))
        # \n \t should be special characters, but they are not handled as that in the function
        self.assertTrue(matchNoSpecialCharactersOnly('azAZ09._-\t'))
        self.assertTrue(matchNoSpecialCharactersOnly(' '))

        self.assertFalse(matchNoSpecialCharactersOnly(''))
        self.assertFalse(matchNoSpecialCharactersOnly('a$b'))
        self.assertFalse(matchNoSpecialCharactersOnly('a;b'))

        self.assertRaises(TypeError, matchNoSpecialCharactersOnly, None)

    def testMatchLettersOnly(self):
        self.assertTrue(matchLettersOnly('azAZ'))

        self.assertFalse(matchLettersOnly('azAZ '))
        self.assertFalse(matchLettersOnly('01azAZ'))
        self.assertFalse(matchLettersOnly('azAZ09._-\t'))

        self.assertRaises(TypeError, matchLettersOnly, None)

    def testMatchNoSpaces(self):
        self.assertTrue(matchNoSpaces('azAZ09'))
        self.assertTrue(matchNoSpaces(''))

        self.assertFalse(matchNoSpaces('az AZ 09'))
        self.assertFalse(matchNoSpaces('az\tAZ09'))

        self.assertRaises(TypeError, matchNoSpaces, None)

    def testMatchNumbersOnly(self):
        self.assertTrue(matchNumbersOnly('0123'))
        self.assertTrue(matchNumbersOnly('3.14'))
        self.assertTrue(matchNumbersOnly('-3.14'))
        # bit weird, but that's how the function is written
        self.assertTrue(matchNumbersOnly('800.555.555'))

        self.assertFalse(matchNumbersOnly(''))

        self.assertRaises(TypeError, matchNumbersOnly, None)

    def testMatchPositiveIntegers(self):
        self.assertTrue(matchPositiveIntegers('123'))

        self.assertFalse(matchPositiveIntegers('123.50'))
        self.assertFalse(matchPositiveIntegers('-123'))
        self.assertFalse(matchPositiveIntegers('0'))
        self.assertFalse(matchPositiveIntegers(''))

        self.assertRaises(TypeError, matchPositiveIntegers, None)

    def testMoreThan3Chars(self):
        self.assertTrue(moreThan3Chars('abcd'))
        self.assertTrue(moreThan3Chars('1234'))
        self.assertTrue(moreThan3Chars('    '))
        self.assertTrue(moreThan3Chars('abc'))

        self.assertFalse(moreThan3Chars(''))

        self.assertRaises(TypeError, moreThan3Chars, None)
    def testNotEmptyString(self):
        self.assertTrue(notEmptyString('abcd'))
        self.assertTrue(notEmptyString('1234'))
        self.assertTrue(notEmptyString('    '))
        self.assertTrue(notEmptyString('abc'))
        self.assertFalse(notEmptyString(''))
        self.assertRaises(TypeError, notEmptyString, None)

if __name__ == '__main__':
    unittest.main()
