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


#include <cstdio>
#include <string>
#include <stdexcept>
#include <sstream>

#include "export/FileSequence.h"

#include <pcre.h>

namespace SPI {
namespace FileSequence {
namespace LIBFILESEQUENCE_VERSION_NS {

FileSequence::FileSequence(const std::string& sequenceString)
{
    setSequence(sequenceString);
}

FileSequence::FileSequence(const std::string& prefix, const FrameSet& frameSet, const std::string& suffix)
    : frameSet(frameSet), prefix(prefix), suffix(suffix)
{
    // must parse out dirname/basename
    const char *errptr = NULL;
    int erroffset;

    const int vec_idx_dirname = 2;
    const int vec_idx_basename = 4;

    pcre *re = pcre_compile("^(.*/)?(?:([^/]+?)\\.?)?$", 0, &errptr, &erroffset, NULL);
    if (!re) return;

    int ovector[30];
    int rc = pcre_exec(re, NULL, prefix.c_str(), prefix.length(), 0, 0, ovector, 30);
    if (rc < 0) {
        pcre_free(re);
        throw std::runtime_error("Invalid prefix");
    }

    try {

        if (ovector[vec_idx_dirname] != -1) {
            dirname = prefix.substr(ovector[vec_idx_dirname], ovector[vec_idx_dirname+1] - ovector[vec_idx_dirname]);
        }

        if (ovector[vec_idx_basename] != -1) {
            basename = prefix.substr(ovector[vec_idx_basename], ovector[vec_idx_basename+1] - ovector[vec_idx_basename]);
        }

        pcre_free(re);
    }
    catch (...) {
        pcre_free(re);
        throw;
    }
}

bool
FileSequence::operator==(const FileSequence& fs) const
{
    // try to short circuit with least expensive test first
    return suffix == fs.suffix
        && prefix == fs.prefix
        && frameSet == fs.frameSet;
}

bool
FileSequence::operator!=(const FileSequence& fs) const
{
    return !(*this == fs);
}

std::string
FileSequence::operator[](int index) const
{
    return (*this)(frameSet[index]);
}

std::string
FileSequence::operator()(int frame) const
{
    if (   !frameSet.frameRanges.empty()
        && !frameSet.contains(frame, NULL)) {
        std::ostringstream errmsg;
        errmsg << "Frame " << frame << " is not in file sequence " << frameSet;
        throw std::invalid_argument(errmsg.str());
    }

    return getFilename(frame);
}

int
FileSequence::size() const
{
    return frameSet.size();
}

void
FileSequence::merge(const FileSequence& other)
{
    if (   suffix != other.suffix
        || prefix != other.prefix) {
        std::ostringstream errmsg;
        errmsg << "Cannot merge FileSequence \""
            << *this << "\" with \""
            << other << "\": prefix or suffix does not match.";
        throw std::runtime_error(errmsg.str());
    }

    frameSet.merge(other.frameSet);
}

void
FileSequence::mergeMultiple(const std::vector<FileSequence>& others)
{
    if (others.empty()) {
        return;
    }
    std::vector<FrameSet> otherFrames;
    otherFrames.reserve(others.size());

    for (std::vector<FileSequence>::const_iterator
        fsit = others.begin(), fsend = others.end();
        fsit != fsend;
        ++fsit) {
        if (suffix != fsit->suffix || prefix != fsit->prefix) {
            std::ostringstream errmsg;
            errmsg << "Cannot merge FileSequence \""
                << *this << "\" with \""
                << *fsit << "\": prefix or suffix does not match.";
            throw std::runtime_error(errmsg.str());
        }
        otherFrames.push_back(fsit->frameSet);
    }

    frameSet.mergeMultiple(otherFrames);
}

bool
FileSequence::canMerge(const FileSequence& other) const
{
    return
        suffix == other.suffix
        && prefix == other.prefix
        && frameSet.canMerge(other.frameSet);
}

std::string
FileSequence::toString() const
{
    std::ostringstream ostr;
    ostr << *this;
    return ostr.str();
}

std::ostream&
operator<<(std::ostream& os, const FileSequence& fs)
{
    os << fs.prefix << fs.frameSet;

    int padSize = fs.frameSet.getPadding().asExplicit();

    for (int hash = 0; hash < padSize / 4; ++hash) {
        os << '#';
    }
    for (int at = 0; at < padSize % 4; ++at) {
        os << '@';
    }

    os << fs.suffix;
    return os;
}

namespace {
    struct ParsedSequence {
        ParsedSequence() :
            error(false),
            hasFrameSetString(false),
            hasPadString(false) {}
        bool error;
        std::string prefix;
        std::string dirname;
        std::string basename;
        std::string suffix;
        bool hasFrameSetString;
        std::string frameSetString;
        bool hasPadString;
        std::string padString;
    };

    /** Parse a sequence string.
    */
    struct ParsedSequence ParseSequence(const std::string& sequenceString) {
        const char *errptr = NULL;
        int erroffset;

        const int vec_idx_prefix = 2;
        const int vec_idx_dirname = 4;
        const int vec_idx_basename = 6;
        const int vec_idx_framesetstring = 8;
        const int vec_idx_padstring = 10;
        const int vec_idx_suffix = 12;

        pcre *re = pcre_compile(
            "^" // start anchor
            "((.*/)?" // directory component (optional)
            "(?:" // basename component (optional)
                "([^/]+)\\." // grab anything that isn't a slash up to a period,
                    "(?![0-9]+$)" // but don't allow the remainder of the string to be
                                // just numbers, to catch cases like "foo.0001.1000"
                ")?"
            ")?"
            "([0-9xy:,-]+)?" // frame range part (optional)
            "([#@]+)?" // padding width part (optional)
            "(\\.[^/]*)?" // extension (optional)
            "$", // end anchor
            0, &errptr, &erroffset, NULL);
        if (!re) throw std::runtime_error("Failed to parse regular expression");

        int ovector[30];

        int rc = pcre_exec(re, NULL, sequenceString.c_str(), sequenceString.length(), 0, 0, ovector, 30);
        pcre_free(re);

        struct ParsedSequence parsedResult;

        if (rc < 0) {
            parsedResult.error = true;
            return parsedResult;
        }

        if (ovector[vec_idx_prefix] != -1) {
            parsedResult.prefix = sequenceString.substr(
                ovector[vec_idx_prefix],
                ovector[vec_idx_prefix+1] - ovector[vec_idx_prefix]);
        }

        if (ovector[vec_idx_dirname] != -1) {
            parsedResult.dirname = sequenceString.substr(
                ovector[vec_idx_dirname],
                ovector[vec_idx_dirname+1] - ovector[vec_idx_dirname]);
        }

        if (ovector[vec_idx_basename] != -1) {
            parsedResult.basename = sequenceString.substr(
                ovector[vec_idx_basename],
                ovector[vec_idx_basename+1] - ovector[vec_idx_basename]);
        }

        if (ovector[vec_idx_suffix] != -1) {
            parsedResult.suffix = sequenceString.substr(
                ovector[vec_idx_suffix],
                ovector[vec_idx_suffix+1] - ovector[vec_idx_suffix]);
        }

        if (ovector[vec_idx_framesetstring] != -1) {
            parsedResult.hasFrameSetString = true;
            parsedResult.frameSetString = sequenceString.substr(
                ovector[vec_idx_framesetstring],
                ovector[vec_idx_framesetstring+1] - ovector[vec_idx_framesetstring]);
        }

        if (ovector[vec_idx_padstring] != -1) {
            parsedResult.hasPadString = true;
            parsedResult.padString = sequenceString.substr(
                ovector[vec_idx_padstring],
                ovector[vec_idx_padstring+1] - ovector[vec_idx_padstring]);
        }

        return parsedResult;
    }
}

bool
FileSequence::isSequence(const std::string& sequenceString)
{
    struct ParsedSequence parsedResult = ParseSequence(sequenceString);
    if (parsedResult.error) {
        return false;
    }
    else if (parsedResult.hasFrameSetString
        && !FrameSet::isSequence(parsedResult.frameSetString)) {
        return false;
    }
    else if (!parsedResult.hasPadString
        && (!parsedResult.hasFrameSetString
            || parsedResult.frameSetString.empty())) {
        return false;
    }
    else {
        return true;
    }
}

void
FileSequence::setSequence(const std::string& sequenceString)
{
    struct ParsedSequence parsedResult = ParseSequence(sequenceString);

    if (parsedResult.error) {
        throw std::runtime_error("Failed to parse file sequence");
    }

    prefix = parsedResult.prefix;
    dirname = parsedResult.dirname;
    basename = parsedResult.basename;
    suffix = parsedResult.suffix;

    if (parsedResult.hasFrameSetString) {
        frameSet = FrameSet(parsedResult.frameSetString);
    }
    else {
        frameSet = FrameSet();
    }

    if (parsedResult.hasPadString) {
        int padSize = 0;

        std::string::const_iterator iter = parsedResult.padString.begin();
        for (; iter != parsedResult.padString.end(); ++iter) {
            switch (*iter) {
                case '#': padSize += 4; break;
                case '@': ++padSize; break;
            }
        }

        if (padSize > 1) {
            // Ignore padSize == 1, a single "@" is the same as
            // no padding.  Stick with the guessed implicit padding
            // in this case.
            frameSet.setPadding(Padding(true, padSize));
        }
    }
    else if (parsedResult.frameSetString.empty()) {
        throw std::runtime_error("String does not appear to be a file sequence");
    }

}

void
FileSequence::setPrefix(const std::string& prefix)
{
    const char *errptr = NULL;
    int erroffset;

    const int vec_idx_prefix = 2;
    const int vec_idx_dirname = 4;
    const int vec_idx_basename = 6;

    pcre *re = pcre_compile("^((.*/)?(.+)\\.)$", 0, &errptr, &erroffset, NULL);
    if (!re) return;

    int ovector[30];
    int rc = pcre_exec(re, NULL, prefix.c_str(), prefix.length(), 0, 0, ovector, 30);
    if (rc < 0) {
        pcre_free(re);
        throw std::runtime_error("Invalid prefix value");
    }

    try {

        if (ovector[vec_idx_prefix] != -1) {
            this->prefix = prefix.substr(ovector[vec_idx_prefix], ovector[vec_idx_prefix+1] - ovector[vec_idx_prefix]);
        }

        if (ovector[vec_idx_dirname] != -1) {
            dirname = prefix.substr(ovector[vec_idx_dirname], ovector[vec_idx_dirname+1] - ovector[vec_idx_dirname]);
        }
        else {
            dirname.clear();
        }

        if (ovector[vec_idx_basename] != -1) {
            basename = prefix.substr(ovector[vec_idx_basename], ovector[vec_idx_basename+1] - ovector[vec_idx_basename]);
        }
        else {
            basename.clear();
        }

        pcre_free(re);
    }
    catch (...) {
        pcre_free(re);
        throw;
    }
}

void
FileSequence::setDirname(const std::string& dirname)
{
    if (!dirname.empty() && dirname[dirname.size()-1] != '/') {
        throw std::runtime_error("dirname must end with a slash or be empty");
    }

    this->dirname = dirname;
    prefix = dirname + basename + ".";
}

void
FileSequence::setBasename(const std::string& basename)
{
    if (basename.empty()) {
        throw std::runtime_error("basename may not be empty");
    }

    if (basename.find('/') != basename.npos) {
        throw std::runtime_error("basename may not contain slashes");
    }

    this->basename = basename;
    prefix = dirname + basename + ".";
}

void
FileSequence::setSuffix(const std::string& suffix)
{
    if (!suffix.empty() && suffix[0] != '.') {
        throw std::runtime_error("suffix must begin with a dot or be empty");
    }

    this->suffix = suffix;
}

std::string
FileSequence::getFilename(int frame) const
{
    int padSize = frameSet.padding.asExplicit();

    char buf[32];
#ifdef WIN32
    _snprintf(buf, 32, "%0*d", padSize, frame);
#else
    snprintf(buf, 32, "%0*d", padSize, frame);
#endif
    return prefix + buf + suffix;
}

std::string
FileSequence_iterator::operator*() const
{
    return fs->getFilename(*fiter);
}

FileSequence_iterator&
FileSequence_iterator::operator++()
{
    ++fiter;
    return *this;
}

FileSequence_iterator
FileSequence_iterator::operator++(int)
{
    FileSequence_iterator clone = *this;
    operator++();
    return clone;
}

bool
FileSequence_iterator::_atEnd() const
{
    return fiter._atEnd();
}

}
}
}
