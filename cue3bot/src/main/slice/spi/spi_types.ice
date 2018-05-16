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


#ifndef SPI_TYPES_ICE
#define SPI_TYPES_ICE

/**
 * Design Notes
 * ============
 *
 * Optional Values
 * ---------------
 *
 * The Slice language does not have a native option type, such as the
 * ability to set a variable to null in Java or Scala (for object
 * types), undef or Perl or None in Python.  Instead, option types are
 * represented as a sequence of the type, where the sequence contains
 * zero or one values.
 *
 * Naming Conventions
 * ------------------
 *
 * 1) Sequences types all end in Seq.
 * 2) Optional types all end in Opt.
 * 3) Set types all end in Set.
 **/

/*
 * $HeadURL$
 * $LastChangedDate$
 * $LastChangedBy$
 * $LastChangedRevision$
 */

[["java:package:com.imageworks.common"]]
[["python:package:spi"]]
module SpiIce
{
    /**
     * Sequences of builtins.
     **/
    sequence<bool> BoolSeq;
    sequence<byte> ByteSeq;
    sequence<double> DoubleSeq;
    sequence<float> FloatSeq;
    sequence<int> IntSeq;
    sequence<long> LongSeq;
    sequence<string> StringSeq;

    /**
     * Optionals of builtins.
     **/
    sequence<bool> BoolOpt;
    sequence<byte> ByteOpt;
    sequence<double> DoubleOpt;
    sequence<float> FloatOpt;
    sequence<int> IntOpt;
    sequence<long> LongOpt;
    sequence<string> StringOpt;

    /**
     * Sequences of sequences.
     **/
    sequence<ByteSeq> ByteSeqSeq;

    /**
     * Optionals of sequences.
     **/
    sequence<ByteSeq> ByteSeqOpt;

    /**
     * Sets of builtins.
     **/
    ["java:type:java.util.HashSet<String>:java.util.HashSet<String>"]
    sequence<string> StringSet;
};

#endif

/*
 * Local Variables:
 * mode: c++
 * End:
 */
