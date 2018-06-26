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


#ifndef FRAMERANGE_H
#define FRAMERANGE_H

#include "ns.h"

#include <string>
#include <vector>

namespace SPI {
namespace FileSequence {
namespace LIBFILESEQUENCE_VERSION_NS {

class FrameRange;

/** \defgroup Objects Objects
    \defgroup Iterators Iterators of Objects
    \defgroup Utilities Utility Functions
*/

/** Frame range iterator.

    \ingroup Iterators
*/
class FrameRange_iterator {
public:
    FrameRange_iterator() : index(-1), fr(NULL) {}
    FrameRange_iterator(int index, const FrameRange* fr) : index(index), fr(fr) {}

    /** Return frame number at iterator position.
    */
    int operator*() const;

    /** Step to next frame number.
    */
    FrameRange_iterator& operator++();

    /** Step to next frame number.
    */
    FrameRange_iterator operator++(int);
    bool operator==(const FrameRange_iterator& o) const
        { return index == o.index; }
    bool operator!=(const FrameRange_iterator& o) const
        { return index != o.index; }
    bool _atEnd() const;
private:
    int index;
    const FrameRange* fr;
};

class FrameSet;

/** Object to represent a frame range, the smallest unit of a frame set.

    A frame range consists of an \p inTime, an \p outTime, and a \p stepSize
    or \p interleaveSize.

    Examples:
    \code
    FrameRange("1-10");
    FrameRange("1-10x3");
    FrameRange("1-10y3");
    FrameRange("10-1x-1");
    FrameRange("1-10:5");
    \endcode

    \ingroup Objects
*/
class FrameRange {
public:
    friend class FileSequence;

    FrameRange() : inTime(0), outTime(0), stepSize(0), invertStep(false), interleaveSize(0) {}

    /** Construct a FrameRange object by parsing a spec.

        \code
        FrameRange("1-10x3");
        FrameRange("1-10y3"); // inverted step
        FrameRange("10-1x-1");
        FrameRange("1"); // same as "1-1x1"
        FrameRange("1-10:5"); // interleave of 5
        \endcode

        A valid spec consists of:

            \li An \p inTime.
            \li An optional hyphen and \p outTime.
            \li An optional \p x or \p y and \p stepSize.
            \li Or an optional \p : and \p interleaveSize.

        If \p outTime is less than \p inTime, \p stepSize must be negative.

        A \p stepSize of 0 produces an empty FrameRange.

        A \p stepSize cannot be combined with a \p interleaveSize.

        A \p stepSize designated with \p p creates an inverted step.
        Frames that would be included with an \p x step are excluded.

        Example: 1-10y3 == 2, 3, 5, 6, 8, 9.

        An inverted \p stepSize of 1 produces an empty FrameRange. An
        inverted \p stepSize of 0 is the same as normal stepSize of 1
        (no step).

        An \p interleaveSize alters the order of frames when iterating over
        the \p FrameRange.  The iterator will first produce the list of frames
        from \p inTime to \p outTime with a stepSize equal to
        \p interleaveSize.  The \p interleaveSize is then divided in half,
        producing another set of frames unique from the first set.  This
        process is repeated until \p interleaveSize reaches 1.

        Example: 1-10:5 == 1, 6, 2, 4, 8, 10, 3, 5, 7, 9.

        \param sequenceString A valid frame range.
        \exception std::runtime_error Thrown if the frame range spec could not
                   be parsed.
        \exception std::runtime_error Thrown if the frame range is invalid.
    */
    FrameRange(const std::string& sequenceString);

    /** Construct a FrameRange object by specifying each component.

        The padding is determined by the number of digits of inTime or
        outTime, whichever is higher (non-explicit).

        \param inTime The start frame number.
        \param outTime The end frame number.
        \param stepSize The amount to increment one frame to compute the next
               frame.  A \p stepSize of 0 produces an empty FrameRange.
        \param invertStep True if the \p stepSize is inverted.
        \param interleaveSize The interleave amount for the FrameRange.
               A \p interleaveSize of 0 disables interleaving.
        \exception std::runtime_error Thrown if the frame range is invalid.
    */
    FrameRange(int inTime, int outTime, int stepSize, bool invertStep, int interleaveSize);

    /** Construct a FrameRange object by specifying each component, plus
        padding.

        \param inTime The start frame number.
        \param outTime The end frame number.
        \param stepSize The amount to increment one frame to compute the next
               frame.  A \p stepSize of 0 produces an empty FrameRange.
        \param invertStep True if the \p stepSize is inverted.
        \param padding The padding of the FrameRange.
        \exception std::runtime_error Thrown if the frame range is invalid.
    */
    FrameRange(int inTime, int outTime, int stepSize, bool invertStep, const Padding& padding);

    /** Construct a FrameRange object by specifying each component, plus
        padding.

        \param inTime The start frame number.
        \param outTime The end frame number.
        \param stepSize The amount to increment one frame to compute the next
               frame.  A \p stepSize of 0 produces an empty FrameRange.
        \param invertStep True if the \p stepSize is inverted.
        \param interleaveSize The interleave amount for the FrameRange.
               A \p interleaveSize of 0 disables interleaving.
        \param padding The padding of the FrameRange.
        \exception std::runtime_error Thrown if the frame range is invalid.
    */
    FrameRange(int inTime, int outTime, int stepSize, bool invertStep, int interleaveSize, const Padding& padding);

    FrameRange(const FrameRange&);

    virtual ~FrameRange();

    FrameRange& operator=(const FrameRange&);

    /** Compare FrameRange with another for equality.

        In order for a FrameRange to be equal to another, the \p inTime,
        \p outTime, and \p stepSize must all be equal.

        \return True if the frame ranges are equal.
    */
    bool operator==(const FrameRange& fs) const;

    /** Compare FrameRange with another for inequality.

        In order for a FrameRange to be equal to another, the \p inTime,
        \p outTime, and \p stepSize must all be equal.

        \return True if the frame ranges are not equal.
    */
    bool operator!=(const FrameRange& fs) const;

    /** Query a frame by index.

        Treating the frame range as an array of frame numbers, return the
        frame number for the given index.

        \param index The index into the frame range.
        \return Number of the frame at given index.
        \exception std::out_of_range Thrown if the index is out of range.
    */
    int operator[](int index) const;

    /** Query membership of frame in frame range.

        \param frame The frame to test for membership.
        \param index If not NULL, set to the index of \p frame if \p contains
               is true.
        \return True if \p frame is in frame range.
        \see FrameRange::index.
    */
    bool contains(int frame, int *index) const;

    /** Query member count of frame range.

        \return Number of frames in \p frame range, may be zero!
    */
    int size() const;

    /** Find nearest neighboring frame number(s) of a given frame.
        \see FileSequence::nearest for a detailed explanation.
    */
    void nearest(int frame, bool *has_left, int *left, bool *has_right, int *right) const;

    /** Query index of frame number in frame range.

        \warning This method ignores \p interleaveSize.

        \return Index of frame.
        \retval -1 Frame range does not contain \p frame.
        \see FrameRange::contains.
    */
    int index(int item) const;

    /** Stringify the FrameRange object.

        The FrameRange object is stringified to the simplest equivalent form.

        \code
        FrameRange("1-10x2").toString() -> "1-10x2"
        FrameRange("1-10x1").toString() -> "1-10"
        FrameRange("1-1x1").toString() -> "1"
        \endcode

        \return String representation of frame range.
    */
    std::string toString() const;

    /** Stringify the FrameRange object.

        \see FrameRange::toString()
    */
    friend std::ostream& operator<<(std::ostream& os, const FrameRange& fr);

    /** Start frame number.
    */
    int inTime;

    /** End frame number.
    */
    int outTime;

    /** Step size, distance from one frame to the next.
    */
    int stepSize;

    /** Invert the step (include frames not matched by step).
    */
    bool invertStep;

    /** Interleave size.
    */
    int interleaveSize;

    /** The padding of this FrameRange.
    */
    Padding padding;

    typedef FrameRange_iterator iterator;

    /** Returns an \p iterator pointing to the beginning of the frame range.
    */
    iterator begin() const;

    /** Returns an \p iterator pointing to the end of the frame range.
    */
    iterator end() const
        { return iterator(); }

    /** Update object by parsing a new sequence string.

        In the event of an error, the state of the FrameRange object is undefined.

        \param sequenceString A valid frame range.
        \exception std::runtime_error Thrown if the frame range spec could not be
                   parsed.
    */
    void setSequence(const std::string& sequenceString);

    /** Check whether a string can be parsed as a frame range.
        \param sequenceString A string which will be checked for validity.
    */
    static bool isSequence(const std::string& sequenceString);

    /** Return a FrameSet object that contains all the same frames as
     *  this FrameRange, but without using an inverted step.
     *  \exception std::runtime_error Thrown if the frame range does not
     *  have an inverted step.
     */
    FrameSet uninvert() const;

private:
    void validate() const;
};

}
using namespace LIBFILESEQUENCE_VERSION_NS;
}
}

#endif
