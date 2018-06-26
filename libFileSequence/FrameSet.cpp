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
#include <iostream>
#include <stdexcept>
#include <numeric>
#include <boost/any.hpp>

#define GCC_VERSION (__GNUC__ * 10000 \
                     + __GNUC_MINOR__ * 100 \
                     + __GNUC_PATCHLEVEL__)

/* Use the best map and set implementation. */
#if GCC_VERSION >= 40400
#  define NATIVE_UNORDERED
#  include <unordered_set>
#  include <unordered_map>
#elif defined(__APPLE__) && defined(__clang__)
#  define TR1_UNORDERED
#  include <tr1/unordered_set>
#  include <tr1/unordered_map>
#else
#  include <set>
#  include <map>
#endif

#include "export/FileSequence.h"

#include <pcre.h>

namespace SPI {
namespace FileSequence {
namespace LIBFILESEQUENCE_VERSION_NS {

#ifdef NATIVE_UNORDERED
template < class V, class H >
struct MapImpl { typedef std::unordered_map<V, H> Type; };
template < class V >
struct SetImpl { typedef std::unordered_set<V> Type; };
#elif defined(TR1_UNORDERED)
template < class V, class H >
struct MapImpl { typedef std::tr1::unordered_map<V, H> Type; };
template < class V >
struct SetImpl { typedef std::tr1::unordered_set<V> Type; };
#else
template < class V, class H >
struct MapImpl { typedef std::map<V, H> Type; };
template < class V >
struct SetImpl { typedef std::set<V> Type; };
#endif

FrameSet::FrameSet(const std::string& sequenceString)
{
    setSequence(sequenceString);
}

FrameSet::FrameSet(const std::string& sequenceString, int p)
{
    setSequence(sequenceString);
    padding.reset(true, p);
    setPadding(padding);
}

bool
FrameSet::operator==(const FrameSet& fs) const
{
    // With regard to padding, FrameSets are considered
    // equal if their paddings are compatible, rather
    // than strictly equal.
    return !!(padding & fs.padding)
        && frameRanges == fs.frameRanges;
}

bool
FrameSet::operator!=(const FrameSet& fs) const
{
    return !(*this == fs);
}

int
FrameSet::operator[](int index) const
{
    if (index < 0) {
        index += size();
        if (index < 0) {
            throw std::out_of_range("Index out of range");
        }
    }

    FrameSet::frameRanges_t::const_iterator iter = frameRanges.begin();
    for (; iter != frameRanges.end(); ++iter) {
        int rangeLength = (*iter).size();
        if (rangeLength <= index) {
            index -= rangeLength;
            continue;
        }
        return (*iter)[index];
    }
    throw std::out_of_range("Index out of range");
}

bool
FrameSet::contains(int frame, int *index) const
{
    int accum = 0;
    FrameSet::frameRanges_t::const_iterator iter = frameRanges.begin();
    for (; iter != frameRanges.end(); ++iter) {
        int fr_index;
        int *fr_index_p = NULL;

        // avoid passing an index pointer to FrameRange::contains
        // if no index is desired, to avoid unnecessary computation.
        if (index) {
            fr_index_p = &fr_index;
        }

        if ((*iter).contains(frame, fr_index_p)) {
            if (index) {
                *index = accum + fr_index;
            }
            return true;
        }
        else if (index) {
            accum += (*iter).size();
        }
    }
    return false;
}

struct get_size : public std::binary_function<int, FrameRange, int>
{
    int operator() (int result, const FrameRange& fr) {
        return result + fr.size();
    }
};

int
FrameSet::size() const
{
    return std::accumulate(frameRanges.begin(), frameRanges.end(), 0, get_size());
}

void
FrameSet::nearest(int frame, bool *has_left, int *left, bool *has_right, int *right) const
{
    *has_left = false;
    *has_right = false;

    FrameSet::frameRanges_t::const_iterator iter = frameRanges.begin();
    for (; iter != frameRanges.end(); ++iter) {
        bool fr_has_left, fr_has_right;
        int fr_left, fr_right;
        (*iter).nearest(frame, &fr_has_left, &fr_left, &fr_has_right, &fr_right);

        if (!*has_left) {
            *has_left = fr_has_left;
            *left = fr_left;
        }
        else if (fr_has_left) {
            *left = std::max(*left, fr_left);
        }

        if (!*has_right) {
            *has_right = fr_has_right;
            *right = fr_right;
        }
        else if (fr_has_right) {
            *right = std::min(*right, fr_right);
        }
    }
}

struct NormRange {
    NormRange(int start_index=0, int start_value=0)
        : start_index(start_index), start_value(start_value),
            count(1), inrange(true), step(std::pair<bool, int>(false, 0)) {}

    void end() {
        inrange = false;
        if (!step.first) {
            step.first = true;
            step.second = 1;
        }
    }

    int start_index;
    int start_value;
    int count;
    bool inrange;
    std::pair<bool, int> step;
};

struct end_range : public std::unary_function<std::pair<const int, NormRange>, void>
{
    void operator() (std::pair<const int, NormRange>& x) {
        x.second.end();
    }
};

struct sort_any : public std::binary_function<boost::any, boost::any, bool>
{
    // at sort time, the types are always int
    bool operator() (const boost::any& a, const boost::any&b) {
        int ia = boost::any_cast<int>(a);
        int ib = boost::any_cast<int>(b);
        return ia < ib;
    }
};

void
FrameSet::normalize()
{
    // this process is very expensive for long sequences,
    // so it is profitable to check if running this is necessary
    // first
    if (isNormal()) return;

    // pass the frame list through a set to eliminate
    // duplicates
    SetImpl<int>::Type frameset;
    {
        iterator iter = begin();
        for (; iter != end(); ++iter) {
            frameset.insert(*iter);
        }
    }
    std::vector<boost::any> framevec(frameset.size());
    std::copy(frameset.begin(), frameset.end(), framevec.begin());
    std::sort(framevec.begin(), framevec.end(), sort_any());

    for (;;) {
        // find the start of each range
        MapImpl<int, NormRange>::Type ranges;

        std::vector<boost::any>::const_iterator iter = framevec.begin();
        for (int i = 0; iter != framevec.end(); ++iter, ++i) {
            if ((*iter).type() == typeid(int)) {
                int frame = boost::any_cast<int>(*iter);

                // Does this item extend or complete
                // any existing ranges?
                MapImpl<int, NormRange>::Type::iterator iter = ranges.begin();
                for (; iter != ranges.end(); ++iter) {
                    NormRange& r = (*iter).second;

                    if (!r.inrange) {
                        continue;
                    }

                    if (!r.step.first) {
                        // the second item determines
                        // the step amount
                        r.step.first = true;
                        r.step.second = frame - r.start_value;
                        ++r.count;
                    }
                    else {
                        // a third or later item must be in the range
                        if (frame == r.start_value + r.count * r.step.second) {
                            ++r.count;
                        }
                        else {
                            // range is complete
                            r.end();
                        }
                    }
                }

                // Start a range for this item
                ranges[i] = NormRange(i, frame);
            }
            else {
                // found a FrameRange(),
                // this ends all ranges
                std::for_each(ranges.begin(), ranges.end(), end_range());
            }
        }

        // end all ranges
        std::for_each(ranges.begin(), ranges.end(), end_range());

        // choose the range with the highest member count,
        // turn that into a frameRange object
        {
            int most = 0;
            int most_index;
            int most_step;
            MapImpl<int, NormRange>::Type::const_iterator iter = ranges.begin();
            for (; iter != ranges.end(); ++iter) {
                const int k = (*iter).first;
                const NormRange& r = (*iter).second;
                if (   r.count > most
                    // use the range as a tie-breaker
                    || (r.count == most && r.step.second > most_step)) {
                    most = r.count;
                    most_index = k;
                    most_step = r.step.second;
                }
            }

            if (most > 0) {
                const NormRange& r = ranges[most_index];
                int inTime = boost::any_cast<int>(framevec[most_index]);
                int outTime = inTime + (r.count - 1) * r.step.second;
                // replace the frames in the list with a FrameRange object
                framevec.erase(framevec.begin()+most_index, framevec.begin()+most_index+r.count);
                if (r.count == 2) {
                    // prefer 1,3 to 1-3x2
                    framevec.reserve(framevec.size() + 2);
                    framevec.insert(framevec.begin()+most_index, FrameRange(inTime, inTime, 1, false, padding));
                    framevec.insert(framevec.begin()+most_index+1, FrameRange(outTime, outTime, 1, false, padding));
                }
                else {
                    framevec.insert(framevec.begin()+most_index, FrameRange(inTime, outTime, r.step.second, false, padding));
                }
            }
            else {
                // repeating until everything is a FrameRange()
                break;
            }
        }
    }

    // framevec now contains a list of FrameRange() objects
    {
        frameRanges.clear();
        frameRanges.reserve(framevec.size());
        std::vector<boost::any>::const_iterator iter = framevec.begin();
        for (; iter != framevec.end(); ++iter) {
            frameRanges.push_back(boost::any_cast<FrameRange>(*iter));
        }
    }
}

bool
FrameSet::mergeWithoutNormalize(const FrameSet& other)
{
    if (!canMerge(other)) {
        throw std::runtime_error("Mismatched padding");
    }
    if (!frameRanges.empty() && !other.frameRanges.empty()) {
        padding &= other.padding;
    }

    // Common case is extending an existing FrameRange by one frame,
    // check for this and skip normalizing.
    bool need_insert = true;

    // Both FrameSets should only have 1 element, otherwise it is
    // possible to add a duplicate or non-ordered frame to the set.
    if (   frameRanges.size() == 1
        && other.frameRanges.size() == 1

        // This FileSequence must be growing in the positive direction,
        // because merge() is expected to sort the result.
        && frameRanges.back().stepSize > 0

        // The FileSequence being merged in must only contain one
        // frame.
        && other.frameRanges.back().size() == 1

        // And that frame must be the next frame after the end
        // of the current FrameRange.
        && other.frameRanges.back().inTime
            == frameRanges.back().outTime
                + frameRanges.back().stepSize) {

        need_insert = false;
        frameRanges.back().outTime += frameRanges.back().stepSize;
    }
    else if (frameRanges.empty()) {
        // merging frames into an empty set results in an empty set
        return false;
    }
    else if (other.frameRanges.empty()) {
        // merging in an empty set results in an empty set
        frameRanges.clear();
        return false;
    }

    if (need_insert) {
        frameRanges.insert(
            frameRanges.end(),
            other.frameRanges.begin(),
            other.frameRanges.end());
    }

    return need_insert;
}

void
FrameSet::merge(const FrameSet& other)
{
    if (mergeWithoutNormalize(other)) {
        normalize();
    }
}

void
FrameSet::mergeMultiple(const std::vector<FrameSet>& others)
{
    bool normalizeRequired = false;
    for(std::vector<FrameSet>::const_iterator
        it = others.begin(), end = others.end();
        it != end;
        ++it) {
        normalizeRequired |= mergeWithoutNormalize(*it);
    }

    if (normalizeRequired) {
        normalize();
    }
}

bool
FrameSet::canMerge(const FrameSet& other) const
{
    return (frameRanges.empty() || other.frameRanges.empty())
        || (padding & other.padding).asBool();
}

int
FrameSet::index(int item) const
{
    int index;
    if (contains(item, &index)) {
        return index;
    }
    return -1;
}

std::string
FrameSet::toString() const
{
    std::ostringstream ostr;
    ostr << *this;
    return ostr.str();
}

FrameSet::iterator
FrameSet::begin() const
{
    if (!frameRanges.empty()) {
        return iterator(0, frameRanges[0].begin(), this);
    }
    return end();
}

FrameSet_iterator::FrameSet_iterator(int index, FrameRange_iterator fiter, const FrameSet* const fs)
    : index(index), fiter(fiter), fs(fs)
{
    seek_to_valid_position();
}

int
FrameSet_iterator::operator*() const
{
    return *fiter;
}

FrameSet_iterator&
FrameSet_iterator::operator++()
{
    ++fiter;
    seek_to_valid_position();
    return *this;
}

FrameSet_iterator
FrameSet_iterator::operator++(int)
{
    FrameSet_iterator clone = *this;
    operator++();
    return clone;
}

bool
FrameSet_iterator::_atEnd() const
{
    return *this == fs->end();
}

void
FrameSet_iterator::seek_to_valid_position()
{
    for (;;) {
        if (fiter == fs->frameRanges[index].end()) {
            ++index;
            if (index >= (int)fs->frameRanges.size()) {
                index = -1;
                break;
            } else {
                fiter = fs->frameRanges[index].begin();
            }
        } else {
            break;
        }
    }
}

std::ostream&
operator<<(std::ostream& os, const FrameSet& fs)
{
    FrameSet::frameRanges_t::const_iterator iter = fs.frameRanges.begin();
    for (int first=1; iter != fs.frameRanges.end(); ++iter) {
        // skip empty ranges
        if (!(*iter).size()) {
            continue;
        }

        if (!first) {
            os << ",";
        }

        os << *iter;
        first = 0;
    }
    return os;
}

bool
FrameSet::isSequence(const std::string& sequenceString)
{
    std::string::size_type pos = 0;

    while (pos < sequenceString.size()) {
        std::string::size_type comma = sequenceString.find(',', pos);

        if (comma == std::string::npos) {
            return FrameRange::isSequence(
                sequenceString.substr(pos, sequenceString.size() - pos)
            );
        }
        else {
            if (!FrameRange::isSequence(
                sequenceString.substr(pos, comma - pos))) {
                return false;
            }
        }
        pos = comma + 1;
    }
    return true;
}

void
FrameSet::setSequence(const std::string& sequenceString)
{
    frameRanges.clear();

    // split by commas
    std::string::size_type pos = 0;

    while (pos < sequenceString.size()) {
        std::string::size_type comma = sequenceString.find(',', pos);

        if (comma == std::string::npos) {
            if (pos < sequenceString.size()) {
                FrameRange fr(
                    sequenceString.substr(pos, sequenceString.size() - pos)
                );
                append(fr);
            }
            break;
        } else if (comma - pos > 0) {
            FrameRange fr(sequenceString.substr(pos, comma - pos));
            append(fr);
        }

        pos = comma + 1;
    }
}

void
FrameSet::setPadding(const Padding& padding)
{
    this->padding = padding;
    FrameSet::frameRanges_t::iterator iter = frameRanges.begin();
    for (; iter != frameRanges.end(); ++iter) {
        iter->padding = padding;
    }
}

bool
FrameSet::isNormal() const
{
    // Check if the FrameSet is already normalized.
    //
    // Note: This routine is subject to false-negatives but not
    // false-positives.  It is only intended to quickly opt out
    // of doing a normalization on known pre-normalized cases.
    int l = frameRanges.size();
    if (l == 0) {
        return true;
    }
    else if (l > 1) {
        return false;
    }
    FrameRange fr = frameRanges[0];
    if (fr.stepSize < 0) {
        return false;
    }

    // 1-2 will be normalized to 1,2
    if (fr.outTime == fr.inTime + fr.stepSize) {
        return false;
    }

    return true;
}

void
FrameSet::append(FrameRange& fr)
{
    // If the set is not empty, the new fr padding must be compatible with the
    // existing FrameSet padding.
    if (!frameRanges.empty()) {
        Padding new_padding = padding & fr.padding;

        if (!new_padding) {
            throw std::runtime_error("Mismatched padding");
        }

        FrameSet::frameRanges_t::iterator iter = frameRanges.begin();
        for (; iter != frameRanges.end(); ++iter) {
            iter->padding = new_padding;
        }

        padding = fr.padding = new_padding;
    }
    else {
        // or the padding assumes the padding of the first element
        padding = fr.padding;
    }

    frameRanges.push_back(fr);
}

}
}
}
