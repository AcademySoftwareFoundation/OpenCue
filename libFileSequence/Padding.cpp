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


#include <string>
#include <stdexcept>
#include <iostream>

#include "export/FileSequence.h"

namespace SPI {
namespace FileSequence {
namespace LIBFILESEQUENCE_VERSION_NS {

bool
Padding::checkString(const std::string& num)
{
    size_t l = num.size();
    return ! (l == 0 || (num[0] == '-' && l == 1));
}

void
Padding::initFromString(const std::string& num)
{
    size_t l = num.size();

    if (!checkString(num)) {
        throw std::runtime_error("Malformed number");
    }

    // determine padding
    if (num[0] == '0') {
        if (l == 1) {
            // a lone zero is not explicit
            is_explicit = false;
            digits = l;
            return;
        }

        // explicit padding
        is_explicit = true;
        digits = l;
        return;
    }
    else if (num[0] == '-' && num[1] == '0') {
        if (l == 2) {
            // a lone negative zero is not explicit
            is_explicit = false;
            digits = l;
            return;
        }

        // explicit padding
        is_explicit = true;
        digits = l;
        return;
    }
    else {
        is_explicit = false;
        digits = l;
        return;
    }
}

static const Padding nullObject;

Padding
Padding::operator&(const Padding& o) const
{
    if (digits == 0 || o.digits == 0) {
        // one or the other is invalid
        return nullObject;
    }

    if (is_explicit) {
        if (o.is_explicit) {
            // when both is explicit, the other must match
            if (digits == o.digits) {
                return *this;
            }
            else {
                return nullObject;
            }
        }
        else {
            // when only one is explict,  it wins
            return *this;
        }
    }
    else {
        if (o.is_explicit) {
            // when only one is explict,  it wins
            return o;
        }
        else {
            // when neither is explicit, the smaller digits wins
            return Padding(false, std::min(digits, o.digits));
        }
    }
}

bool
Padding::asBool() const
{
    return digits != 0;
}

std::ostream&
operator<<(std::ostream& os, const Padding& padding)
{
    os << "Padding(" << (padding.is_explicit ? "true" : "false")
       << ", " << padding.digits << ")";
    return os;
}

}
}
}
