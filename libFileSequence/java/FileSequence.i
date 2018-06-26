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

%module JFileSequence

/* Add a loadLibrary call to the JNI class */
%pragma(java) jniclasscode=%{
    static { System.loadLibrary("JFileSequence"); }
%}

%include "typemaps.i"
%include "exception.i"
%include "std_string.i"
%include "std_vector.i"

%include "export/ns.h"

%define RENAME_OPS(class)
%rename(get)        SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class::operator[];
%rename(assign)     SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class::operator=;
%rename(equals)     SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class::operator==;
%rename(ne)         SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class::operator!=;
%rename(bwand)      SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class::operator&;
%rename(bwandeq)    SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class::operator&=;
%rename(notop)      SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class::operator!;
%rename(call)       SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class::operator();
%enddef

%define RENAME_OPS_ITER(class)
RENAME_OPS(class)
%rename(next)       SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class ## _iterator::operator++;
%rename(equals)     SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class ## _iterator::operator==;
%rename(ne)         SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::class ## _iterator::operator!=;
%enddef

RENAME_OPS(Padding)
RENAME_OPS_ITER(FrameRange)
RENAME_OPS_ITER(FrameSet)
RENAME_OPS_ITER(FileSequence)

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

// these affect FileSequence::nearest and FrameSet::nearest so in java
// the has_left / left params can be passed as single element arrays
// allowing nearest to return multiple values back to the caller.
%apply bool *OUTPUT { bool *has_left };
%apply bool *OUTPUT { bool *has_right };
%apply int *OUTPUT { int *left };
%apply int *OUTPUT { int *right };

%include "export/Padding.h"
%include "export/FrameRange.h"
%include "export/FrameSet.h"
%include "export/FileSequence.h"
%include "export/FindSequence.h"

// swig-y explicit template instantiation
void FindSequence(
    const std::vector< std::string >& files,
    std::vector< SPI::FileSequence::LIBFILESEQUENCE_VERSION_NS::FileSequence >& seqs,
    std::vector< std::string >& nonseqs);
