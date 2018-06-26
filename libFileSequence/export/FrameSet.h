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


#ifndef FRAMESET_H
#define FRAMESET_H

#include "ns.h"
#include "FrameRange.h"

#include <string>
#include <vector>

namespace SPI {
namespace FileSequence {
namespace LIBFILESEQUENCE_VERSION_NS {

class FrameSet;

/** Frame set iterator.

    \ingroup Iterators
*/
class FrameSet_iterator {
public:
    FrameSet_iterator() : index(-1), fs(NULL) {}
    FrameSet_iterator(int index, const FrameSet* fs) : index(index), fs(fs) {}
    FrameSet_iterator(int index, FrameRange_iterator fiter, const FrameSet* fs);

    /** Return frame number at iterator position.
    */
    int operator*() const;

    /** Step to next frame number.
    */
    FrameSet_iterator& operator++();

    /** Step to next frame number.
    */
    FrameSet_iterator operator++(int);
    bool operator==(const FrameSet_iterator& o) const
        { return index == o.index && (index == -1 || fiter == o.fiter); }
    bool operator!=(const FrameSet_iterator& o) const
        { return index != o.index || (index != -1 && fiter != o.fiter); }
    bool _atEnd() const;
private:
    int index;
    FrameRange_iterator fiter;
    const FrameSet* fs;

    void seek_to_valid_position();
};

/** Object to represent a frame set, a collection of frame ranges.

    A frame set is an ordered list of zero or more FrameRange objects.

    Examples:
    \code
    FrameSet("1-10");
    FrameSet("1-10,20-30x2");
    FrameSet("1-10,-4,8--8x-1");
    \endcode

    \ingroup Objects
*/
class FrameSet {
public:
    friend class FileSequence;
    friend class FrameRange;

    /** Construct an empty FrameSet.
    */
    FrameSet() {}

    /** Construct a FrameSet object by parsing a spec.

        \code
        FrameSet("1-10x3,2-20x4");
        \endcode

        A valid filespec consists of:

            \li An optional valid FrameRange.
            \li Zero or more comma and another valid FrameRange.

        \see FrameRange::FrameRange for a description of a valid FrameRange.

        \param sequenceString A valid frame set.
        \exception std::runtime_error Thrown if the frame set spec could not
                   be parsed.
        \exception std::runtime_error Thrown if any frame range is invalid.
    */
    FrameSet(const std::string& sequenceString);

    /** Construct a FrameSet object by parsing a spec, override padding.

        \see FrameSet(const std::string&)
    */
    FrameSet(const std::string& sequenceString, int padding);
    virtual ~FrameSet() {}

    /** Compare FrameSet with another for equality.

        In order for a FrameSet to be equal to another, it must have
        the same number of frame ranges, with the frame range at each
        index comparing equal.

        \return True if the frame sets are equal.
    */
    bool operator==(const FrameSet& fs) const;

    /** Compare FrameSet with another for inequality.

        In order for a FrameSet to be equal to another, it must have
        the same number of frame ranges, with the frame range at each
        index comparing equal.

        \return True if the frame sets are not equal.
    */
    bool operator!=(const FrameSet& fs) const;

    /** Query a frame by index.

        Treating the frame set as an array of frame numbers, return the
        frame number for the given index.

        \param index The index into the frame set.
        \return Number of the frame at given index.
        \exception std::out_of_range Thrown if the index is out of range.
    */
    int operator[](int index) const;

    /** Query membership of frame in frame set.

        \param frame The frame to test for membership.
        \param index If not NULL, set to the index of \p frame if \p contains
               is true.
        \return True if \p frame is in frame set.
        \see FrameSet::index.
    */
    bool contains(int frame, int *index) const;

    /** Query member count of frame set.

        Computes the sum of the size of each FrameRange in the frame set.

        \return Number of frames in \p frame set, may be zero!
    */
    int size() const;

    /** Find nearest neighboring frame number(s) of a given frame.
        \see FileSequence::nearest for a detailed explanation.
    */
    void nearest(int frame, bool *has_left, int *left, bool *has_right, int *right) const;

    /** Reduce frame set to the simplest equivalent form.
        \see FileSequence::normalize for a detailed explanation.
    */
    void normalize();

    /** Merge two FrameSets.
        \see FileSequence::merge for a detailed explanation.
    */
    void merge(const FrameSet& other);

    /** Merge this FrameSet with multiple others (batch for efficiency).
    */
    void mergeMultiple(const std::vector<FrameSet>& others);

    /** Check whether two FrameSets can be merged.
        Two FrameSets may be merged if they have compatible padding.
    */
    bool canMerge(const FrameSet& other) const;

    /** Query index of frame number in frame set.

        \return Index of frame.
        \retval -1 Frame set does not contain \p frame.
        \see FrameSet::contains.
    */
    int index(int item) const;

    /** Stringify the FrameSet object.

        The FrameSet object is stringified to the simplest equivalent form.
        Empty frame ranges are omitted.

        \see FrameRange::toString
    */
    std::string toString() const;

    /** Stringify the FrameSet object.

        \see FrameSet::toString
    */
    friend std::ostream& operator<<(std::ostream& os, const FrameSet& fs);

    typedef FrameSet_iterator iterator;

    /** Returns an \p iterator pointing to the beginning of the frame set.
    */
    iterator begin() const;

    /** Returns an \p iterator pointing to the end of the frame set.
    */
    iterator end() const
        { return iterator(-1, this); }

    /** Update object by parsing a new sequence string.

        In the event of an error, the state of the FrameSet object is undefined.

        \param sequenceString A valid frame set.
        \exception std::runtime_error Thrown if the frame set spec could not be
                   parsed.
    */
    void setSequence(const std::string& sequenceString);

    /** Check whether a string can be parsed as a frame set.
        \param sequenceString A string which will be checked for validity.
    */
    static bool isSequence(const std::string& sequenceString);

    /** Padding of the FrameSet.

        The padding of the FrameSet assumes the padding of the first
        FrameRange added to it.

        Subsequent FrameRanges must be compatible with the existing padding
        value.  The padding value of the FrameSet and all FrameRanges is
        updated with the result of ANDing the new padding with the existing
        padding.
    */
    void setPadding(const Padding& padding);

    const Padding& getPadding() const
        { return padding; }

    typedef std::vector< FrameRange > frameRanges_t;

    /** Vector of FrameRange objects
    */
    frameRanges_t frameRanges;

private:
    bool isNormal() const;
    void append(FrameRange& fr);
    bool mergeWithoutNormalize(const FrameSet& other);

    Padding padding;
};

}
using namespace LIBFILESEQUENCE_VERSION_NS;
}
}

#endif
