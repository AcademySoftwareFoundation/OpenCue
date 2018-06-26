/*
 * Copyright (c) 2018 Sony Pictures Imageworks Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */


#ifndef PADDING_H
#define PADDING_H

#include "ns.h"

#include <string>

namespace SPI {
namespace FileSequence {
namespace LIBFILESEQUENCE_VERSION_NS {

/** Object to represent frame number padding.

    A frame number string with leading zeros is defined as having
    explicit padding.  Negative numbers may also have explicit
    padding, and the minus character is counted.

    \code
    "0001" : explicit padding of 4
    "-001" : also, explicit padding of 4
    \endcode

    When no leading zeros are present, the padding is not explicit
    and the number may be padded or may not be.

    \code
      "1" : no padding
    "100" : possible padding of 2 or 3, or none.  Definitely not padded to 4 or more.
    \endcode

    A padding value of 1 means no padding, and the string "0" is not considered
    to have explicit padding.

    \ingroup Objects
*/
struct Padding {
    Padding() : is_explicit(false), digits(0) {}
    Padding(bool is_explicit, unsigned int digits)
        : is_explicit(is_explicit), digits(digits) {}
    void reset(bool e, unsigned int d)
    {
        is_explicit = e;
        digits = d;
    }

    /** Construct a Padding object by parsing a number string.

        \param num A string of a number to parse.
        \return A new Padding object.
        \exception std::runtime_error Thrown if the string is invalid.
    */
    static Padding fromString(const std::string& num)
    {
        Padding returnValue;
        returnValue.initFromString(num);
        return returnValue;
    }

    /** Check whether a string can be used to initialize a Padding.
        \param num A string which will be checked for validity.
    */
    static bool checkString(const std::string& num);

    /** Initialize a Padding object by parsing a number string.
        (avoids object creation overhead)

        \param num A string of a number to parse.
        \exception std::runtime_error Thrown if the string is invalid.
    */
    void initFromString(const std::string& num);

    /** Bitwise Or of two Padding objects.

        Two Padding objects can be combined if:

            \li They are both explicit with the same width; or
            \li Only one is explicit; or
            \li Both are not explicit.

        If either Padding object is invalid, or the two cannot be
        combined, a new object representing an invalid padding
        is returned.

        When one object is explicit, the resulting padding is
        explicit with the same width as the explicit object.

        When neither object is explicit, the resulting padding
        is not explicit and the new width is the lesser of the
        two objects' widths.
    */
    Padding operator&(const Padding& o) const;

    bool asBool() const;

    /** In-place bitwise And.
    */
    Padding& operator&=(const Padding& o)
        { *this = *this & o; return *this; }

    bool operator!() const
        { return digits == 0; }

    /** Compare Padding with another for equality.

        The two objects must have the same "explicity" and width.

        \return True if the padding objects are equal.
    */
    bool operator==(const Padding& o) const
        { return is_explicit == o.is_explicit && digits == o.digits; }

    /** Query the padding width but return the count only if the padding is
        explicit.

    */
    unsigned int asExplicit() const
        { return is_explicit ? digits : 1; }

    friend std::ostream& operator<<(std::ostream& os, const Padding& padding);

    /** True if the padding is explicit.
    */
    bool is_explicit;

    /** The padding width.  Zero if padding is undefined.
    */
    unsigned int digits;
};

}
using namespace LIBFILESEQUENCE_VERSION_NS;
}
}

#endif
