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


#define _LARGEFILE_SOURCE
#define _LARGEFILE64_SOURCE
#define _FILE_OFFSET_BITS 64

#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <dirent.h>

#include <vector>
#include <deque>
#include <algorithm>

#include "export/FindSequence.h"

namespace SPI {
namespace FileSequence {
namespace LIBFILESEQUENCE_VERSION_NS {

void
FindSequenceOnDisk(const std::string& path,
    std::vector<FileSequence>& seqs,
    std::vector<std::string>& nonseqs,
    bool recursive,
    bool all)
{
    std::string _path = path;

    while (_path.size() > 1 && _path[_path.size()-1] == '/') {
        _path = _path.substr(0, _path.size()-1);
    }

    std::deque<std::string> directories;

    std::string curdir = _path;

    for (;;) {
        std::vector<std::string> files;

        DIR *d = opendir(curdir.c_str());
        if (d) {
            struct dirent *r;
            while ((r = readdir(d))) {
                std::string d_name = r->d_name;

                if (d_name == "." || d_name == "..") continue;
                if (d_name[0] == '.' && !all) continue;

                std::string fullname = curdir
                    + std::string("/")
                    + d_name;

                struct stat buf;
                int statr = stat(fullname.c_str(), &buf);
                if (!statr) {
                    if (S_ISDIR(buf.st_mode)) {
                        if (recursive) {
                            directories.push_back(fullname);
                        }
                    } else {
                        files.push_back(fullname);
                    }
                }
            }

            closedir(d);
        }

        /* FindSequence has to iterate over the known sequences to check
           if any file fits in one, so it gets really slow to accumulate
           all the sequences into 'seqs' as we go.
        */
        std::vector<FileSequence> internal_seqs;
        std::vector<std::string> internal_nonseqs;

        std::sort(files.begin(), files.end());
        FindSequence(files, internal_seqs, internal_nonseqs);

        seqs.reserve(seqs.size() + internal_seqs.size());
        seqs.insert(seqs.end(), internal_seqs.begin(), internal_seqs.end());

        nonseqs.reserve(nonseqs.size() + internal_nonseqs.size());
        nonseqs.insert(nonseqs.end(), internal_nonseqs.begin(), internal_nonseqs.end());

        if (directories.empty()) break;

        curdir = directories.front();
        directories.pop_front();
    }
}

}
}
}
