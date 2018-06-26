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

#if SWIG_VERSION < 0x010337
#error This project requires SWIG 1.3.37 or later.
#endif

%define DOCSTRING
"Image File Sequence Parser

The Python usage differs from the C++ version in the following ways:

    Iteration

    It is not necessary to use the begin() and end() methods to create
    iterators, as the objects support native Python iteration.

        fs = FileSequence(\"foo.1-10#.bar\")
        for filename in fs:
            print filename

    List Emulation

        Use len(fs) rather than fs.size().
        Use \"x in fs\" rather than fs.contains(x).

    Misc

        Use str(fs) rather than fs.toString().

        index(frame) returns None rather than -1 if the frame is not found.

        The nearest() method has been made easier to use.
            nearest(frame) -> left, right
        left or right may be None.

        FindSequence and FindSequenceOnDisk return seqs, nonseqs as a tuple.
            FindSequence(files) -> seqs, nonseqs
            FindSequenceOnDisk(path, recursive=False, all=False) -> seqs, nonseqs
"
%enddef

%module (docstring=DOCSTRING, "threads"=1) FileSequence

%feature("autodoc", "0");

/* Disable GIL releasing for everything. */
%feature("nothread");

%include "typemaps.i"
%include "exception.i"
%include "std_string.i"
%include "std_vector.i"
%include "cpointer.i"

%include "export/ns.h"

%define RENAME_OPS(class)
%rename(__getitem__)    SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class::operator[];
%rename(__len__)        SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class::size;
%rename(__contains__)   SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class::contains;
%rename(__str__)        SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class::toString;
%rename(__iter__)       SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class::begin;
%ignore                 SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class::end;
%rename(next)           SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class ## _iterator::operator++;
%enddef

RENAME_OPS(FrameRange)
RENAME_OPS(FrameSet)
RENAME_OPS(FileSequence)

%rename(_FindSequenceOnDisk)  FindSequenceOnDisk;
%rename(_FindSequence)  FindSequence;

%{

#include <stdexcept>
#include "export/FileSequence.h"
#include "export/FindSequence.h"

using namespace SPI::FileSequence;

%}

%template(file_sequence_vector) std::vector<SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::FileSequence>;
%template(frame_set_vector) std::vector<SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::FrameSet>;
%template(frame_range_vector) std::vector<SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::FrameRange>;
%template(string_vector) std::vector<std::string>;

%exception {
    try {
        $action
    } catch (const std::out_of_range& e) {
        SWIG_exception(SWIG_IndexError, e.what());
    } catch (const std::exception& e) {
        SWIG_exception(SWIG_ValueError, e.what());
    }
}

%pointer_functions(int, intp);
%pointer_functions(bool, boolp);

%feature("shadow") nearest(int,bool*,int*,bool*,int*) const %{
def nearest(self, frame):
    has_left = new_boolp()
    left = new_intp()
    has_right = new_boolp()
    right = new_intp()
    try:
        $action(self, frame, has_left, left, has_right, right)

        if boolp_value(has_left):
            l = intp_value(left)
        else:
            l = None

        if boolp_value(has_right):
            r = intp_value(right)
        else:
            r = None

        return l,r
    finally:
        delete_boolp(has_left)
        delete_intp(left)
        delete_boolp(has_right)
        delete_intp(right)
%}

%feature("shadow") contains(int,int*) const %{
def __contains__(self, frame):
    """__contains__(self, frame) -> bool"""
    return $action(self, frame, None)

def contains_with_index(self, frame):
    """Check if frame is in sequence, and also return index of frame."""
    idx = new_intp()
    try:
         r = $action(self, frame, idx)
         return r, intp_value(idx)
    finally:
        delete_intp(idx)
%}

%pythonprepend operator==(const FrameRange&) const %{
        if args[0] is None and len(self) == 0: return True
        if not isinstance(args[0], FrameRange): return False
%}

%pythonprepend operator==(const FrameSet&) const %{
        if args[0] is None and len(self) == 0: return True
        if not isinstance(args[0], FrameSet): return False
%}

%pythonappend index(int) const %{
        if val == -1: val = None
%}

%pythonprepend SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::FrameRange_iterator::operator++(int) %{
        if self._atEnd():
            raise StopIteration
        cur = self.__ref__()
%}

%pythonappend SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::FrameRange_iterator::operator++(int) %{
        return cur
%}

%pythonprepend SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::FrameSet_iterator::operator++(int) %{
        if self._atEnd():
            raise StopIteration
        cur = self.__ref__()
%}

%pythonappend SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::FrameSet_iterator::operator++(int) %{
        return cur
%}

%pythonprepend SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::FileSequence_iterator::operator++(int) %{
        if self._atEnd():
            raise StopIteration
        cur = self.__ref__()
%}

%pythonappend SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::FileSequence_iterator::operator++(int) %{
        return cur
%}

%include "export/Padding.h"
%include "export/FrameRange.h"
%include "export/FrameSet.h"
%include "export/FileSequence.h"
/* Reset (enable) GIL releasing for everything, so FindSequence and
   FindSequenceOnDisk release the GIL. */
%feature("nothread", "");
%include "export/FindSequence.h"

// swig-y explicit template instantiation
void FindSequence(
    const std::vector< std::string >& files,
    std::vector< SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::FileSequence >& seqs,
    std::vector< std::string >& nonseqs);

/* Disable GIL releasing for everything. */
%feature("nothread");

%pythoncode %{
def _wrap_vectors(seqs, nonseqs):
    # The vector objects have some annoying gotchas, such as
    # pulling an item with __getitem__ only pulls out a pointer
    # to memory still owned by the vector (without increasing the
    # reference count to the vector), so it is up to the caller to
    # keep the vector alive manually.
    #
    # To hide this technical detail, populate a normal python list
    # with real refcounted objects.

    _seqs = []
    _nonseqs = []

    for fs in seqs:
        # seqs are FileSequence objects, fake a copy constructor
        _seqs.append(FileSequence(fs.getPrefix(), fs.frameSet, fs.getSuffix()))

    for f in nonseqs:
        # nonseqs are plain strings (filenames)
        _nonseqs.append(str(f))

    return _seqs, _nonseqs

def FindSequence(files):
    seqs = file_sequence_vector()
    nonseqs = string_vector()

    _FindSequence(files, seqs, nonseqs)

    return _wrap_vectors(seqs, nonseqs)

def FindSequenceOnDisk(path, recursive=False, all=False):
    seqs = file_sequence_vector()
    nonseqs = string_vector()

    _FindSequenceOnDisk(path, seqs, nonseqs, recursive, all)

    return _wrap_vectors(seqs, nonseqs)

def _str_reduce(self):
    """A suitable __reduce__ method for pickling FileSequence objects."""
    return (self.__class__, (self.__str__(),))

FileSequence.__reduce__ = _str_reduce
FrameSet.__reduce__ = _str_reduce
FrameRange.__reduce__ = _str_reduce
%}
