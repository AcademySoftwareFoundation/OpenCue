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
#include <sstream>
#include <stdexcept>
#include <iostream>

#include <math.h>
#include <errno.h>
#include <limits.h>

#include "export/FileSequence.h"

#include <pcre.h>

#include <vector>
#include <set>
#include <algorithm>

namespace SPI {
namespace FileSequence {
namespace LIBFILESEQUENCE_VERSION_NS {

static int getInterleaveIndexFromFrame(int frame, int inTime, int outTime, int interleaveSize)
{
    int index = -1;
    int beginning = 0;
    bool savedBeginning = false;

    std::set<int> used;
    for (;;) {
        int start = inTime;
        while (start <= outTime) {
            if (used.find(start) == used.end()) {
                index++;
                if (! savedBeginning) {
                    beginning = index;
                    savedBeginning = true;
                }
                if (frame == start)
                    return (index - beginning);
                used.insert(start);
            }
            start += interleaveSize;
        }
        if (interleaveSize == 1) break;
        interleaveSize /= 2;
    }
    return -1;
}

static int getInterleaveFrameFromIndex(int index, int inTime, int outTime, int interleaveSize)
{
    int foundIndex = -1;

    std::set<int> used;
    for (;;) {
        int start = inTime;
        while (start <= outTime) {
            if (used.find(start) == used.end()) {
                if (++foundIndex == index)
                    return start;
                used.insert(start);
            }
            start += interleaveSize;
        }
        if (interleaveSize == 1) break;
        interleaveSize /= 2;
    }
    return -1;
}

FrameRange::FrameRange(const std::string& sequenceString) : inTime(0), outTime(0), stepSize(1)
{
    setSequence(sequenceString);
}

FrameRange::FrameRange(int inTime, int outTime, int stepSize, bool invertStep, int interleaveSize)
    : inTime(inTime), outTime(outTime), stepSize(stepSize), invertStep(invertStep), interleaveSize(interleaveSize)
{
    padding.reset(false,
        std::max(
            1 + (int)(log10f(fabs((float)inTime))),
            1 + (int)(log10f(fabs((float)outTime)))
        )
    );

    validate();
}

FrameRange::FrameRange(int inTime, int outTime, int stepSize, bool invertStep, const Padding& padding)
    : inTime(inTime), outTime(outTime), stepSize(stepSize), invertStep(invertStep), interleaveSize(0), padding(padding)
{
    validate();
}

FrameRange::FrameRange(int inTime, int outTime, int stepSize, bool invertStep, int interleaveSize, const Padding& padding)
    : inTime(inTime), outTime(outTime), stepSize(stepSize), invertStep(invertStep), interleaveSize(interleaveSize), padding(padding)
{
    validate();
}

FrameRange::FrameRange(const FrameRange& fr)
{
    inTime = fr.inTime;
    outTime = fr.outTime;
    stepSize = fr.stepSize;
    invertStep = fr.invertStep;
    interleaveSize = fr.interleaveSize;
    padding = fr.padding;
}

FrameRange::~FrameRange()
{
}

FrameRange&
FrameRange::operator=(const FrameRange& fr)
{
    if (this == &fr) return *this;

    inTime = fr.inTime;
    outTime = fr.outTime;
    stepSize = fr.stepSize;
    invertStep = fr.invertStep;
    interleaveSize = fr.interleaveSize;
    padding = fr.padding;

    return *this;
}

bool
FrameRange::operator==(const FrameRange& fr) const
{
    return    inTime == fr.inTime
           && outTime == fr.outTime
           && stepSize == fr.stepSize
           && invertStep == fr.invertStep
           && interleaveSize == fr.interleaveSize
           && !!(padding & fr.padding);
}

bool
FrameRange::operator!=(const FrameRange& fr) const
{
    return !(*this == fr);
}

int
FrameRange::operator[](int index) const
{
    int r;
    if (invertStep) {
        if (stepSize == 1 || stepSize == -1) {
            // Special case; skipping all frames means empty range.
            throw std::out_of_range("Index out of range");
        }

        if (stepSize > 0) {
            // Basic theory here is the value at the given index will
            // be inTime + index, but also skip ahead an additional
            // amount based on how many times the index divides into
            // the stepSize.
            r = inTime + 1 + index + index / (stepSize - 1);
        }
        else {
            r = inTime - 1 - index - index / (-stepSize - 1);
        }
    }
    else {
        r = inTime + index * stepSize;
    }
    if (stepSize > 0) {
        if (r > outTime) {
            throw std::out_of_range("Index out of range");
        }
    }
    else if (stepSize < 0) {
        if (r < outTime) {
            throw std::out_of_range("Index out of range");
        }
    } else {
        throw std::out_of_range("Index out of range");
    }

    if (interleaveSize > 1) {
        return getInterleaveFrameFromIndex(index, inTime, outTime, interleaveSize);
    }

    return r;
}

bool
FrameRange::contains(int frame, int *index) const
{
    if (interleaveSize > 1) {
        // interleaving forward
        if (frame < inTime) return false;
        if (frame > outTime) return false;

        const int tmpIndex = getInterleaveIndexFromFrame(frame, inTime, outTime, interleaveSize);
        if (tmpIndex < 0) return false;

        if (index) {
            *index = tmpIndex;
        }

        return true;
    }
    else if (stepSize > 0) {
        // stepping forward
        if (frame < inTime) return false;
        if (frame > outTime) return false;

        bool r = ((frame - inTime) % stepSize) == 0;
        if (invertStep) {
            r = !r;
        }
        if (r && index) {
            // caller wants index of item
            if (invertStep) {
                // subtract the number of skipped frames transited
                *index = (frame - inTime - 1) - (frame - inTime - 1) / stepSize;
            }
            else {
                *index = (frame - inTime) / stepSize;
            }
        }
        return r;
    }
    else if (stepSize < 0) {
        // stepping backward
        if (frame > inTime) return false;
        if (frame < outTime) return false;

        bool r = ((inTime - frame) % -stepSize) == 0;
        if (invertStep) {
            r = !r;
        }
        if (r && index) {
            // caller wants index of item
            if (invertStep) {
                *index = (inTime - frame - 1) - (inTime - frame - 1) / -stepSize;
            }
            else {
                *index = (inTime - frame) / -stepSize;
            }
        }
        return r;
    }
    else {
        return false;
    }
}

int
FrameRange::size() const
{
    if (stepSize > 0) {
        if (invertStep) {
            if (stepSize == 1) {
                // Special case; skipping all frames means empty range.
                return 0;
            }

            // The inverted step length is the length of the FrameRange
            // with a step of 1, minus the length of the same FrameRange
            // with a non-inverted step.
            int step1length = outTime - inTime + 1;
            return step1length - ((outTime - inTime) / stepSize + 1);
        }
        else {
            return (outTime - inTime) / stepSize + 1;
        }
    }
    else if (stepSize < 0) {
        if (invertStep) {
            if (stepSize == -1) {
                // Special case; skipping all frames means empty range.
                return 0;
            }

            int step1length = inTime - outTime + 1;
            return step1length - ((inTime - outTime) / -stepSize + 1);
        }
        else {
            return (inTime - outTime) / -stepSize + 1;
        }
    }
    else {
        return 0;
    }
}

void
FrameRange::nearest(int frame, bool *has_left, int *left, bool *has_right, int *right) const
{
    *has_left = false;
    *has_right = false;

    if (invertStep) {
        // We exploit the property that an inverted step sequence
        // can never be missing more than one frame in a row.
        int low;
        int high;

        if (stepSize > 0) {
            low = inTime + 1;

            // If outTime is not contained in the range, the high
            // value is the second largest number.
            if (contains(outTime, NULL)) {
                high = outTime;
            }
            else {
                high = outTime - 1;
            }
        }
        else {
            low = outTime - 1;

            if (contains(inTime, NULL)) {
                high = inTime;
            }
            else {
                high = inTime + 1;
            }
        }

        if (frame < low) {
            *has_right = true;
            *right = low;
            return;
        }
        else if (frame > high) {
            *has_left = true;
            *left = high;
            return;
        }

        // Use contains() hit tests to find the neighbors
        if (contains(frame - 1, NULL)) {
            *has_left = true;
            *left = frame - 1;
        }
        else if (frame - 2 >= low) {
            *has_left = true;
            *left = frame - 2;
        }

        if (contains(frame + 1, NULL)) {
            *has_right = true;
            *right = frame + 1;
        }
        else if (frame + 2 <= high) {
            *has_right = true;
            *right = frame + 2;
        }

        return;
    }

    int low = std::min(inTime, outTime);
    int high = std::max(inTime, outTime);
    int step = abs(stepSize);
    if (frame < low) {
        *has_right = true;
        *right = low;
        return;
    }
    else if (frame > high) {
        *has_left = true;
        *left = high;
        return;
    }

    int lo_near = frame - ((frame - low) % step);
    int hi_near = lo_near + step;
    if (lo_near == frame) {
        lo_near -= step;
    }
    if (lo_near >= low) {
        *has_left = true;
        *left = lo_near;
    }
    if (hi_near <= high) {
        *has_right = true;
        *right = hi_near;
    }
}

int
FrameRange::index(int item) const
{
    int index;
    if (contains(item, &index)) {
        return index;
    }
    return -1;
}

std::string
FrameRange::toString() const
{
    std::ostringstream ostr;
    ostr << *this;
    return ostr.str();
}

FrameRange::iterator
FrameRange::begin() const
{
    if (stepSize == 0)
        return end();
    return iterator(0, this);
}

int
FrameRange_iterator::operator*() const
{
    return (*fr)[index];
}

FrameRange_iterator&
FrameRange_iterator::operator++()
{
    if (++index >= fr->size())
        index = -1;
    return *this;
}

FrameRange_iterator
FrameRange_iterator::operator++(int)
{
    FrameRange_iterator clone = *this;
    operator++();
    return clone;
}

bool
FrameRange_iterator::_atEnd() const
{
    return *this == fr->end();
}

void
FrameRange::validate() const
{
    // see isSequence (matches this)
    if (stepSize > 0 && inTime > outTime) {
        throw std::runtime_error("FrameRange has invalid inTime and outTime");
    }
    else if (stepSize < 0 && inTime < outTime) {
        throw std::runtime_error("FrameRange has invalid inTime and outTime");
    }
    else if (stepSize == 0 && inTime != outTime) {
        throw std::runtime_error("FrameRange has invalid inTime and outTime");
    }
    else if (stepSize == 0 && invertStep) {
        // Do not validate. This combination should be transformed
        // into stepSize = 1, invertStep = false elsewhere.
        throw std::runtime_error("FrameRange has invalid inverted stepSize");
    }
    else if (interleaveSize < 0) {
        throw std::runtime_error("FrameRange has invalid interleave");
    }
    else if (stepSize != 1 && interleaveSize != 0) {
        throw std::runtime_error("FrameRange has stepSize and interleaveSize");
    }
}

std::ostream&
operator<<(std::ostream& os, const FrameRange& fr)
{
    os << fr.inTime;
    if (fr.outTime != fr.inTime) {
        os << "-" << fr.outTime;
    }
    if (fr.stepSize != 1) {
        os << (fr.invertStep ? "y" : "x") << fr.stepSize;
    }
    else if (fr.interleaveSize > 0) {
        os << ":" << fr.interleaveSize;
    }
    return os;
}

namespace
{
    struct ParsedFrameRange
    {
        ParsedFrameRange() :
            error(false),
            hasOutTime(false) {}
        bool error;
        int inTime;
        std::string inTimeStr;
        bool hasOutTime;
        int outTime;
        std::string outTimeStr;
        int interleaveSize;
        int stepSize;
        bool invertStep;
    };

    /** Parse a FrameRange string.
    */
    struct ParsedFrameRange ParseFrameRange(const std::string& sequenceString) {
        const char *errptr = NULL;
        int erroffset;

        const int vec_idx_intime = 2;
        const int vec_idx_outtime = 4;
        const int vec_idx_stepsize = 6;
        const int vec_idx_intlsize = 8;
        const int vec_idx_exceptsize = 10;

        pcre *re = pcre_compile("^(-?\\d+)(?:-(-?\\d+)(?:x(-?\\d+)|:(\\d+)|y(-?\\d+))?)?$", 0, &errptr, &erroffset, NULL);
        if (!re) {
            throw std::runtime_error("Error parsing regular expression for FrameRange.");
        }

        int ovector[30];
        int rc = pcre_exec(re, NULL, sequenceString.c_str(), sequenceString.length(), 0, 0, ovector, 30);
        pcre_free(re);

        struct ParsedFrameRange parsedResult;

        if (rc < 0) {
            parsedResult.error = true;
            return parsedResult;
        }

        if (ovector[vec_idx_intime] != -1) {
            parsedResult.inTimeStr = sequenceString.substr(
                ovector[vec_idx_intime],
                ovector[vec_idx_intime+1] - ovector[vec_idx_intime]);
            errno = 0;
            long int val = strtol(parsedResult.inTimeStr.c_str(),
                                  (char **)NULL, 10);
            if (errno != 0 || val > INT_MAX || val < INT_MIN) {
                parsedResult.error = true;
                return parsedResult;
            }
            parsedResult.inTime = static_cast<int>(val);
        }

        if (ovector[vec_idx_outtime] != -1) {
            parsedResult.hasOutTime = true;
            parsedResult.outTimeStr = sequenceString.substr(
                ovector[vec_idx_outtime],
                ovector[vec_idx_outtime+1] - ovector[vec_idx_outtime]);
            errno = 0;
            long int val = strtol(parsedResult.outTimeStr.c_str(),
                                  (char **)NULL, 10);
            if (errno != 0 || val > INT_MAX || val < INT_MIN) {
                parsedResult.error = true;
                return parsedResult;
            }
            parsedResult.outTime = static_cast<int>(val);
        }
        else {
            parsedResult.outTime = parsedResult.inTime;
        }

        if (ovector[vec_idx_stepsize] != -1) {
            std::string stepSizeStr = sequenceString.substr(
                ovector[vec_idx_stepsize],
                ovector[vec_idx_stepsize+1] - ovector[vec_idx_stepsize]);
            errno = 0;
            long int val = strtol(stepSizeStr.c_str(), (char **)NULL, 10);
            if (errno != 0 || val > INT_MAX || val < INT_MIN) {
                parsedResult.error = true;
                return parsedResult;
            }
            parsedResult.stepSize = static_cast<int>(val);
        }
        else {
            parsedResult.stepSize = 1;
        }

        if (ovector[vec_idx_intlsize] != -1) {
            std::string interleaveSizeStr = sequenceString.substr(
                ovector[vec_idx_intlsize],
                ovector[vec_idx_intlsize+1] - ovector[vec_idx_intlsize]);
            errno = 0;
            long int val = strtol(interleaveSizeStr.c_str(), (char **)NULL,
                                  10);
            if (errno != 0 || val > INT_MAX || val < INT_MIN) {
                parsedResult.error = true;
                return parsedResult;
            }
            parsedResult.interleaveSize = val;
            if (parsedResult.interleaveSize == 1) {
                parsedResult.interleaveSize = 0;
            }
        }
        else {
            parsedResult.interleaveSize = 0;
        }

        if (ovector[vec_idx_exceptsize] != -1) {
            std::string exceptSizeStr = sequenceString.substr(
                ovector[vec_idx_exceptsize],
                ovector[vec_idx_exceptsize+1] - ovector[vec_idx_exceptsize]);
            errno = 0;
            long int val = strtol(exceptSizeStr.c_str(), (char **)NULL, 10);
            if (errno != 0 || val > INT_MAX || val < INT_MIN) {
                parsedResult.error = true;
                return parsedResult;
            }
            parsedResult.stepSize = static_cast<int>(val);
            if (parsedResult.stepSize == 0) {
                // Special case, treat this as if no step was
                // specified, since skipping no frames means
                // keeping all frames.
                parsedResult.stepSize = 1;
                parsedResult.invertStep = false;
            }
            else {
                parsedResult.invertStep = true;
            }
        }
        else {
            parsedResult.invertStep = false;
        }

        return parsedResult;
    }
}

bool
FrameRange::isSequence(const std::string& sequenceString)
{
    struct ParsedFrameRange r = ParseFrameRange(sequenceString);
    if (r.error) {
        return false;
    }
    else if (!Padding::checkString(r.inTimeStr)) {
        return false;
    }
    else if (r.hasOutTime) {
        if (!Padding::checkString(r.outTimeStr)) {
            return false;
        }
        Padding i = Padding::fromString(r.inTimeStr);
        Padding o = Padding::fromString(r.outTimeStr);
        if (!(i & o)) {
            return false;
        }
    }
    else if (
        // see validate
        (r.stepSize > 0 && r.inTime > r.outTime)
        || (r.stepSize < 0 && r.inTime < r.outTime)
        || (r.stepSize == 0 && r.inTime != r.outTime)
        || (r.interleaveSize < 0)
        || (r.stepSize != 1 && r.interleaveSize != 0)
    ) {
        return false;
    }
    return true;
}

void
FrameRange::setSequence(const std::string& sequenceString)
{
    struct ParsedFrameRange parsedResult = ParseFrameRange(sequenceString);

    if (parsedResult.error) {
        throw std::runtime_error("Failed to parse frame range: " + sequenceString);
    }

    inTime = parsedResult.inTime;
    outTime = parsedResult.outTime;

    padding.initFromString(parsedResult.inTimeStr);
    if (parsedResult.hasOutTime) {
        Padding o_padding = Padding::fromString(parsedResult.outTimeStr);

        if (!(padding & o_padding)) {
            std::ostringstream errmsg;
            errmsg << "Mismatched padding '" << parsedResult.inTimeStr
                << "' != '" << parsedResult.outTimeStr << "'";
            throw std::runtime_error(errmsg.str());
        }
        padding &= o_padding;
    }

    stepSize = parsedResult.stepSize;
    invertStep = parsedResult.invertStep;
    interleaveSize = parsedResult.interleaveSize;

    validate();
}

FrameSet
FrameRange::uninvert() const
{
    if (!invertStep) {
        throw std::runtime_error("FrameRange not inverted");
    }

    FrameSet result;

    FrameRange_iterator iter = begin();
    FrameRange_iterator last = end();
    for (; iter != last; ++iter) {
        int frame = *iter;
        FrameRange fr(frame, frame, 1, false, padding);
        result.append(fr);
    }

    // It may seem like a good idea to normalize the result, but
    // normalize might change the order of the frames (if this
    // FrameRange has reverse ordered frames), and normalize may
    // some day detect and create inverted step frame ranges.

    return result;
}

}
}
}
