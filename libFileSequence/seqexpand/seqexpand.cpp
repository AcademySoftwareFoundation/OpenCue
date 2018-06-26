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

#include <vector>

namespace FS = SPI::FileSequence;

int
main(int argc, char **argv)
{
    std::vector<std::string> output;

    size_t max_length = 0;

    for (int i = 1; i < argc; ++i) {
        try {
            FS::FileSequence fs = FS::FileSequence(argv[i]);
            FS::FileSequence::iterator iter = fs.begin();
            FS::FileSequence::iterator last = fs.end();
            for (; iter != last; ++iter) {
                output.push_back(*iter);
                max_length = std::max(max_length, output.back().size());
            }
        }
        catch (...) {
            output.push_back(argv[i]);
            max_length = std::max(max_length, output.back().size());
        }
    }

    // How many columns are needed, based on the maximum length of any
    // entry and the desired 2 spaces between columns?
    int cols = 78 / (max_length + 2);
    // Need at least one column.
    if (cols == 0) {
        cols = 1;
    }

    // How many rows will there be? Need to round up.
    int rows = static_cast<int>(static_cast<float>(output.size()) / static_cast<float>(cols) + 0.5f);
    // ... and be at least 1.
    if (rows == 0) {
        rows = 1;
    }

    for (int row = 0; row < rows; ++row) {
        bool blank = true;

        for (int col = 0; col < cols; ++col) {
            size_t cell = col * rows + row;
            if (cell >= output.size()) {
                continue;
            }

            blank = false;

            std::string &value = output[cell];
            std::cout << value;
            for (size_t pad = value.size(); pad < max_length; ++pad) {
                std::cout << " ";
            }

            if (col != cols - 1) {
                std::cout << "  ";
            }
        }

        if (!blank) {
            std::cout << "\n";
        }
    }

    return 0;
}
