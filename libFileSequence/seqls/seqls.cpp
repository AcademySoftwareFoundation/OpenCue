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


#include "FindSequence.h"

#include <iostream>
#include <algorithm>

using namespace SPI::FileSequence;

int
main(int argc, char **argv)
{
    std::string dir;

    if (argc == 1) {
        dir = ".";
    }
    else {
        dir = argv[1];
    }

    std::vector<FileSequence> seqs;
    std::vector<std::string> nonseqs;

    FindSequenceOnDisk(dir, seqs, nonseqs, true, true);

    for (
        std::vector<FileSequence>::const_iterator iter = seqs.begin();
        iter != seqs.end();
        ++iter
    ) {
        nonseqs.push_back(iter->toString());
    }

    std::sort(nonseqs.begin(), nonseqs.end());

    for (
        std::vector<std::string>::const_iterator iter = nonseqs.begin();
        iter != nonseqs.end();
        ++iter
    ) {
        std::cout << *iter << "\n";
    }

    return 0;
}
