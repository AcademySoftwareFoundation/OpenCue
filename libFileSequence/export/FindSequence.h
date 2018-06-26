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


#ifndef FINDSEQUENCE_H
#define FINDSEQUENCE_H

#include "FileSequence.h"

#include <vector>
#include <map>
#include <iostream>

namespace SPI {
namespace FileSequence {
namespace LIBFILESEQUENCE_VERSION_NS {

    namespace {
        struct SequenceKey {
            SequenceKey(std::string p, std::string s) :
                prefix(p), suffix(s), collision(0) { }

            std::string prefix;
            std::string suffix;
            int collision;

            bool operator<(const SequenceKey& other) const {
                if (prefix == other.prefix) {
                    if (suffix == other.suffix) {
                        return collision < other.collision;
                    }
                    else {
                        return suffix < other.suffix;
                    }
                }
                else {
                    return prefix < other.prefix;
                }
            }
        };

        std::ostream& operator<<(std::ostream& os, const SequenceKey& k) {
            return os << "('" << k.prefix << "', '" << k.suffix
                << "' (" << k.collision << "))";
        }

        typedef std::map< SequenceKey, std::vector<FileSequence> > SequenceDict;
    }

/** Create FileSequence object(s) from a series of filenames.

    The order of files is not important.

    \warning seqs and nonseqs are not cleared!

    \param files An STL container containing a list of files to combine into
           FileSequence(s).
    \param seqs One or more FileSequence objects will be returned in seqs.
           Existing contents are ignored.
    \param nonseqs Any file not recognized as a FileSequence will be returned
           in nonseqs.

    \see FindSequenceOnDisk

    \ingroup Utilities
*/
template<class Container>
void
FindSequence(const Container& files,
    std::vector<FileSequence>& seqs,
    std::vector<std::string>& nonseqs)
{
    // Overall strategy:
    //  First, read in all files, weed out non-sequences,
    //      and group them by like prefix/suffix (and mergability);
    //  Then, merge together sequences with like prefix/suffix.

    // map for in-progress sequences, from (prefix, suffix) to list of file sequences
    SequenceDict sequencesDict; // in-progress sequences

    // For each file, check if it's a sequence member; if it is,
    //  put it in the in-progress sequences dict according to prefix/suffix.
    typename Container::const_iterator
        fiter = files.begin(),
        fend = files.end();
    for (; fiter != fend; ++fiter) {
        if (!FileSequence::isSequence(*fiter)) {
            nonseqs.push_back(*fiter);
            continue;
        }

        FileSequence fs = FileSequence(*fiter);

        // A file can't be a sequence too, maybe it is a filename
        // that looks like a file sequence.
        if (fs.size() != 1) {
            nonseqs.push_back(*fiter);
            continue;
        }

        // Prefix and suffix match are necessary for mergability,
        //  but test canMerge and include an extra value in the key
        //  in case prefix/suffix are not sufficient. (Avoid knowing
        //  to much about FileSequence.)
        // However, assume that mergability is transitive. (Padding
        //  would be the counter case, but we earlier excluded any sequences
        //  which are not a single frame and .: none have explicit padding.)

        SequenceKey sequenceKey(fs.getPrefix(), fs.getSuffix());

        SequenceDict::iterator entryIt;
        do {
            entryIt = sequencesDict.find(sequenceKey);
            if (entryIt != sequencesDict.end()) {
                if (!fs.canMerge(entryIt->second[0])) {
                    sequenceKey.collision++;
                    entryIt = sequencesDict.end();
                }
            }
            else {
                std::vector<FileSequence> newEntry;
                std::pair<SequenceDict::iterator, bool> result =
                    sequencesDict.insert(std::make_pair(sequenceKey, newEntry));
                if (result.second) {
                    entryIt = result.first;
                }
            }
        }
        while (entryIt == sequencesDict.end());

        entryIt->second.push_back(fs);
    }

    // Merge the list of sequences in each prefix/suffix entry
    //  and add the merged sequences to the output vector.
    for (SequenceDict::iterator
        dit = sequencesDict.begin(), dend = sequencesDict.end();
        dit != dend;
        ++dit) {
        if (dit->second.empty()) {
            continue;
        }
        FileSequence fs = dit->second.back();
        dit->second.pop_back();
        fs.mergeMultiple(dit->second);
        seqs.push_back(fs);
    }
}

/** Create FileSequence object(s) from a directory on disk.

    \warning seqs and nonseqs are not cleared!

    \param path A directory on disk to list and combine into FileSequence(s).
    \param seqs One or more FileSequence objects will be returned in seqs.
    \param nonseqs Any file not recognized as a FileSequence will be returned
           in nonseqs.
    \param recursive Search for files in subdirectories.
    \param all Include "hidden" files that start with a dot.

    \see FindSequence

    \ingroup Utilities
*/
extern void
FindSequenceOnDisk(const std::string& path,
    std::vector<FileSequence>& seqs,
    std::vector<std::string>& nonseqs,
    bool recursive,
    bool all);

}
using namespace LIBFILESEQUENCE_VERSION_NS;
}
}

#endif
