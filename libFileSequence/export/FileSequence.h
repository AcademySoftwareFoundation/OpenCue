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


#ifndef FILESEQUENCE_H
#define FILESEQUENCE_H

/** \mainpage FileSequence - Image File Sequence Parser

    \section intro_sec Introduction

    This is library for parsing a "filespec" and for generating filenames in
    an image sequence.

    A filespec describes a collection of related files, differing only by
    a frame number.

    \code
    image.0001.jpg
    image.0002.jpg
    image.0003.jpg
    ...
    image.0008.jpg
    image.0009.jpg
    image.0010.jpg

    "image.1-10#.jpg"
    \endcode

    Typical usage is to parse a filespec and iterate over the filenames.

    \code
    FileSequence fs = FileSequence("image.1-10#.jpg");

    FileSequence::iterator iter = fs.begin();
    for (; iter != fs.end(); ++iter) {
        std::cout << *iter << std::endl;
    }

    // "image.0001.jpg"
    // "image.0002.jpg"
    // ...
    // "image.0009.jpg"
    // "image.0010.jpg"
    \endcode

    Filenames can by queried by frame number.

    \code
    fs(4); // "image.0004.jpg"
    \endcode

    Or by index.

    \code
    fs[4]; // "image.0005.jpg"
    \endcode
*/

#include "ns.h"
#include "Padding.h"
#include "FrameRange.h"
#include "FrameSet.h"

namespace SPI {
namespace FileSequence {
/** Version-specific namespace.

    Typical usage:

    \code
    #include <FileSequence.h>
    using namespace SPI::FileSequence;
    \endcode
*/
namespace LIBFILESEQUENCE_VERSION_NS {

class FileSequence;

/** \defgroup Objects Objects
    \defgroup Iterators Iterators of Objects
    \defgroup Utilities Utility Functions
*/

/** File sequence iterator.

    \ingroup Iterators
*/
class FileSequence_iterator {
public:
    FileSequence_iterator(const FileSequence* fs) : fs(fs) {}
    FileSequence_iterator(FrameSet_iterator fiter, const FileSequence* fs)
        : fiter(fiter), fs(fs) {}

    /** Return filename at iterator position.
    */
    std::string operator*() const;

    /** Step to next filename.
    */
    FileSequence_iterator& operator++();

    /** Step to next filename.
    */
    FileSequence_iterator operator++(int);
    bool operator==(const FileSequence_iterator& o) const
        { return fiter == o.fiter; }
    bool operator!=(const FileSequence_iterator& o) const
        { return fiter != o.fiter; }
    bool _atEnd() const;
private:
    FrameSet_iterator fiter;
    const FileSequence* fs;
};

/** Object to represent a file sequence.

    Represent a sequence of files, typically images.

    For example:
    \code
    FileSequence("foo.1-27x2#.rla");
    \endcode

    No relationship to actual files on disk is presumed by a FileSequence
    object.

    \see FindSequenceOnDisk for a way to construct FileSequence objects
    from files on disk.

    \ingroup Objects
*/
class FileSequence {
public:
    friend class FileSequence_iterator;

    FileSequence() : prefix("."), suffix(".") {}

    /** Construct a FileSequence object by parsing a filespec.

        \code
        // Canonical example.
        FileSequence("foo.1-10#.bar");
        // Pad width will be guessed.
        FileSequence("foo.1-10.bar");
        // A directory component is allowed.
        FileSequence("/baz/foo.1-10#.bar");
        \endcode

        A valid filespec consists of:

            \li A \p prefix up to and including a period.
            \li A valid \p FrameSet.
            \li Zero or more pad width characters [#@].
            \li A \p suffix beginning with a leading period.

        Either prefix and suffix may be empty.  If non-empty, a period must
        separate it from the FrameSet.

        \see FrameSet::FrameSet for a description of a valid FrameSet.

        \param sequenceString A valid file sequence.
        \exception std::runtime_error Thrown if the filespec could not be parsed.
    */
    FileSequence(const std::string& sequenceString);

    /** Construct a FileSequence object by specifying each component.

        The dirname and basename values are computed from the prefix.

        \param prefix The optional dirname and basename of the file sequence.
               It should end with a period.
        \param frameSet A FrameSet object.
        \param suffix The file extension. It should begin with a period.
        \exception std::runtime_error Thrown if the prefix is not valid.
    */
    FileSequence(const std::string& prefix, const FrameSet& frameSet, const std::string& suffix);
    virtual ~FileSequence() {}

    /** Compare FileSequence with another for equality.

        In order for a FileSequence to be equal to another, the \p prefix and
        \p suffix must be equal, as well as the \p padSize, and finally the
        \p frameSet.

        \return True if the file sequences are equal.
    */
    bool operator==(const FileSequence& fs) const;

    /** Compare FileSequence with another for inequality.

        \return True if the file sequences are not equal.
    */
    bool operator!=(const FileSequence& fs) const;

    /** Query a filename by index.

        Treating the file sequence as an array of filename, return the
        filename for the given index.

        \param index The index into the file sequence.
        \return Filename of the frame at given index.
    */
    std::string operator[](int index) const;

    /** Query a filename by frame.

        \param frame The frame number of the desired filename.
        \return Filename of the frame.
        \exception std::invalid_argument Thrown if \p frame is not a member of \p frameSet.
    */
    std::string operator()(int frame) const;

    /** Query membership of frame in \p frameSet.

        \param frame The frame to test for membership.
        \param index If not NULL, set to the index of \p frame if \p contains
               is true.
        \return True if \p frame is in \p frameSet.
        \see FrameSet::contains.
    */
    bool contains(int frame, int *index) const
        { return frameSet.contains(frame, index); }

    /** Query member count of \p frameSet.

        \return Number of frames in \p frameSet, may be zero!
        \see FrameSet::size.
    */
    int size() const;

    /** Find nearest neighboring frame number(s) of a given frame.

        Useful for finding the nearest frames in a \p frameSet to a frame
        that is not present.

        The order of frames in the \p frameSet is ignored for purposes of
        finding neighbors.  If \p frame is present in the \p frameSet, it
        is ignored for purposes of finding neighbors.

        The largest frame number less than \p frame is returned as the left
        neighbor.  If no frame number meets this criterion, \p has_left is
        false.

        The smallest frame number greater than \p frame is returned as the
        right neighbor.  If no frame number meets this criterion, \p has_right
        is false.

        \code
        FileSequence fs = FileSequence("foo.1-10x3.bar");
        // Frames: 1  4  7  10
        fs.nearest(0, ...);  // left: false, right: 1
        fs.nearest(1, ...);  // left: false, right: 4
        fs.nearest(2, ...);  // left: 1,     right: 4
        \endcode

        \param frame The frame to find neighboring frames, the frame does not
               need to be a member of \p frameSet.
        \param has_left True if there is a neighbor to the left.
        \param left The neighboring left frame if \p has_left is true.
        \param has_right True if there is a neighbor to the right.
        \param right The neighboring right frame if \p has_right is true.
        \see FrameSet::nearest.
    */
    void nearest(int frame, bool *has_left, int *left, bool *has_right, int *right) const
        { frameSet.nearest(frame, has_left, left, has_right, right); }

    /** Query index of frame number in \p frameSet.

        \return Index of frame.
        \retval -1 \p frameSet does not contain \p frame.
        \see FrameSet::index.
    */
    int index(int item) const
        { return frameSet.index(item); }

    /** Reduce \p frameSet to the simplest equivalent form.

        Normalize will analyze the frames in \p frameSet and detect frame steps,
        and combine runs of \p FrameRanges where possible.

        Normalization first explodes the current ranges to their component
        frames, then rebuilds ranges to produce a new set of non-overlapping
        ranges. In the process, it will:
            - remove duplicates
            - prefer to individuals to a range with only [start, end]
            - prefer to put a frame in (i) the (eventually) larger range,
              and as a tie-breaker (ii) the range with the larger step.

        \code
        "1-2" -> "1,2"
        "1,2,3" -> "1-3"
        "1,3,5" -> "1-5x2"
        \endcode

        \warning Frame order will be lost!
    */
    void normalize()
        { frameSet.normalize(); }

    /** Merge two FileSequences.

        FileSequence will have the frames of a second FileSequence added to
        it.

        If the second FileSequence does not match this FileSequence, except
        for the \p frameSet, an exception will be thrown and this FileSequence
        left unmodified.

        \warning Upon a successful merge, the FileSequence will be normalized.

        \param other A second FileSequence to merge into this one.
        \exception std::runtime_error Thrown if the FileSequences cannot be
                   merged.
    */
    void merge(const FileSequence& other);

    /** Merge one FileSequence with a number of others (batch for efficiency).
    */
    void mergeMultiple(const std::vector<FileSequence>& others);

    /** Check whether this FileSequence can be merged with another.
    */
    bool canMerge(const FileSequence& other) const;

    /** Stringify the FileSequence object.

        \return String representation of the file sequence.
    */
    std::string toString() const;

    /** Stringify a FileSequence object.

        \see FileSequence::toString
    */
    friend std::ostream& operator<<(std::ostream& os, const FileSequence& fs);

    typedef FileSequence_iterator iterator;

    /** Returns an \p iterator pointing to the beginning of the FileSequence.
    */
    iterator begin() const
        { return iterator(frameSet.begin(), this); }

    /** Returns an \p iterator pointing to the end of the FileSequence.
    */
    iterator end() const
        { return iterator(frameSet.end(), this); }

    /** Update object by parsing a new sequence string.

        In the event of an error, the state of the FileSequence object is undefined.

        \param sequenceString A valid file sequence.
        \exception std::runtime_error Thrown if the filespec could not be parsed.
    */
    void setSequence(const std::string& sequenceString);

    /** Check whether a string can be parsed as a file sequence.
        \param sequenceString A string which will be checked for validity.
    */
    static bool isSequence(const std::string& sequenceString);

    /** The optional dirname and basename of the file sequence, including
        trailing period, e.g., \p "/baz/foo." for \p "/baz/foo.1#.bar".
    */
    const std::string& getPrefix() const
        { return prefix; }

    /** Set the file sequence prefix.

        The prefix may contain a path component and must end in a period.

        The dirname and basename will be updated appropriately.

        \exception std::runtime_error Thrown if the new prefix is not
                   formatted properly.
    */
    void setPrefix(const std::string& prefix);

    /** The optional directory component of \p prefix, e.g., \p "/baz/" for
        \p "/baz/foo.1#.bar".
    */
    const std::string& getDirname() const
        { return dirname; }

    /** Set the file sequence dirname.

        The dirname may be empty, or if not empty, must end in a forward
        slash.

        The prefix will be updated appropriately.

        \exception std::runtime_error Thrown if the new dirname is not
                   formatted properly.
    */
    void setDirname(const std::string& dirname);

    /** The base filename of the file sequence, excluding any directory
        component, e.g., \p "foo" for \p "/baz/foo.1#.bar".
    */
    const std::string& getBasename() const
        { return basename; }

    /** Set the file sequence basename.

        The basename may not be empty or contain a forward slash.

        \warning It should not end with a dot. setBasename used to require a
        trailing dot but this was changed to fix a consistency problem.

        The prefix will be updated appropriately.

        \exception std::runtime_error Thrown if the new basename is not
                   formatted properly.
    */
    void setBasename(const std::string& basename);

    /** The extension of the file sequence, including leading period,
        e.g., \p ".bar" for \p "/baz/foo.1#.bar".
    */
    const std::string& getSuffix() const
        { return suffix; }

    /** Set the file sequence suffix.

        The suffix must begin with a period, or be empty.

        \exception std::runtime_error Thrown if the new suffix is not
                   formatted properly.
    */
    void setSuffix(const std::string& suffix);

    /** Return the padding width of the file sequence, or zero if unknown.

        \see FrameSet::getPadding
    */
    int getPadSize() const
        { return frameSet.padding.asExplicit(); }

    /** The set of frame numbers in the file sequence, may be empty.
    */
    FrameSet frameSet;

private:
    // Does not check if frame is member of frameSet,
    // use operator() in public interface instead
    std::string getFilename(int frame) const;

    std::string prefix;
    std::string dirname;
    std::string basename;
    std::string suffix;
};

}
using namespace LIBFILESEQUENCE_VERSION_NS;
}
}

#endif
