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


#include "FileSequenceTest.h"
#include "export/FileSequence.h"
#include "export/FindSequence.h"

#include <sstream>
#include <stdexcept>
#include <vector>
#include <set>
#include <iostream>
#include <algorithm>
#include <iterator>

#ifdef PROFILING
CPPUNIT_TEST_SUITE_REGISTRATION(FindSequenceTest);
#else
CPPUNIT_TEST_SUITE_REGISTRATION(FileSequenceTest);
CPPUNIT_TEST_SUITE_REGISTRATION(FrameRangeTest);
CPPUNIT_TEST_SUITE_REGISTRATION(FrameSetTest);
CPPUNIT_TEST_SUITE_REGISTRATION(FindSequenceTest);
CPPUNIT_TEST_SUITE_REGISTRATION(PaddingTest);
#endif

using namespace SPI::FileSequence;

struct fs_test_data {
    const char *fs;
    const char *prefix;
    const char *dirname;
    const char *basename;
    const char *suffix;
    const int padSize;
    const FrameSet *frameSet;
};

static void
testFileSequence(fs_test_data* data)
{
    fs_test_data* d = data;
    int i = 0;

    while (d->fs) {
        ++i;

        FileSequence fs;

        try {
            fs.setSequence(d->fs);
        }
        catch (const std::runtime_error& e) {
            std::stringstream errmsg;
            errmsg << "Test index " << i << ", fs '" << d->fs << "' Failed to parse";
            std::string e = errmsg.str();
            CPPUNIT_ASSERT_MESSAGE(e.c_str(), 0);

            ++d;
            continue;
        }

        if (d->prefix != NULL) {
            std::stringstream errmsg;
            errmsg << "Test index " << i << ", fs '" << d->fs << "'";
            errmsg << " Expected prefix '" << d->prefix << "', got '" << fs.getPrefix() << "'";
            std::string e = errmsg.str();
            CPPUNIT_ASSERT_MESSAGE(e.c_str(), fs.getPrefix() == d->prefix);
        }
        if (d->dirname != NULL) {
            std::stringstream errmsg;
            errmsg << "Test index " << i << " , fs '" << d->fs << "'";
            errmsg << " Expected dirname '" << d->dirname << "', got '" << fs.getDirname() << "'";
            std::string e = errmsg.str();
            CPPUNIT_ASSERT_MESSAGE(e.c_str(), fs.getDirname() == d->dirname);
        }
        if (d->basename != NULL) {
            std::stringstream errmsg;
            errmsg << "Test index " << i << " , fs '" << d->fs << "'";
            errmsg << " Expected basename '" << d->basename << "', got '" << fs.getBasename() << "'";
            std::string e = errmsg.str();
            CPPUNIT_ASSERT_MESSAGE(e.c_str(), fs.getBasename() == d->basename);
        }
        if (d->suffix != NULL) {
            std::stringstream errmsg;
            errmsg << "Test index " << i << " , fs '" << d->fs << "'";
            errmsg << " Expected suffix '" << d->suffix << "', got '" << fs.getSuffix() << "'";
            std::string e = errmsg.str();
            CPPUNIT_ASSERT_MESSAGE(e.c_str(), fs.getSuffix() == d->suffix);
        }
        {
            std::stringstream errmsg;
            errmsg << "Test index " << i << " , fs '" << d->fs << "'";
            errmsg << " Expected padSize '" << d->padSize << "', got '" << fs.getPadSize() << "'";
            std::string e = errmsg.str();
            CPPUNIT_ASSERT_MESSAGE(e.c_str(), fs.getPadSize() == d->padSize);
        }
        if (d->frameSet != NULL) {
            std::stringstream errmsg;
            errmsg << "Test index " << i << " , fs '" << d->fs << "'";
            errmsg << " Expected frameSet '" << *d->frameSet << "', got '" << fs.frameSet << "'";
            std::string e = errmsg.str();
            CPPUNIT_ASSERT_MESSAGE(e.c_str(), fs.frameSet == *d->frameSet);
        }

        if (d->frameSet) {
            // confirm the procedural contructor produces a matching object

            try {
                FileSequence fs2 = FileSequence(d->prefix, *d->frameSet, d->suffix);

                std::stringstream errmsg;
                errmsg << "Test index " << i << " , fs '" << d->fs << "'";
                errmsg << " Alternate contructor doesn't match";
                std::string e = errmsg.str();
                CPPUNIT_ASSERT_MESSAGE(e.c_str(), fs == fs2);
            }
            catch (const std::runtime_error& e) {
                std::stringstream errmsg;
                errmsg << "Test index " << i << ", fs '" << d->fs << "' Failed to construct";
                std::string e = errmsg.str();
                CPPUNIT_ASSERT_MESSAGE(e.c_str(), 0);
            }
        }

        if (d->frameSet) {
            delete d->frameSet;
            d->frameSet = NULL;
        }

        ++d;
    }
}

void
FileSequenceTest::testVariousFileSequences()
{
    fs_test_data data[] = {
        // fs                       prefix              dirname         basename            suffix      pad     frameset
        { "foo.1-1#.bar",           "foo.",             "",             "foo",              ".bar",     4,   new FrameSet("1-1") },
        { "foo.1-1:2#.bar",         "foo.",             "",             "foo",              ".bar",     4,   new FrameSet("1-1:2") },
        { "foo.#.bar",              "foo.",             "",             "foo",              ".bar",     4,   NULL },
        { "foo.1-15x2#@#@.bar",     "foo.",             "",             "foo",              ".bar",     10,  new FrameSet("1-15x2") },
        { "foo.1-15y2#@#@.bar",     "foo.",             "",             "foo",              ".bar",     10,  new FrameSet("1-15y2") },
        { "foo.1-15x2.bar",         "foo.",             "",             "foo",              ".bar",     1,   new FrameSet("1-15x2") },
        { "someImage.1,3,5#.rla",   "someImage.",       "",             "someImage",        ".rla",     4,   new FrameSet("1,3,5") },
        { "foo.#.exr.tx",           "foo.",             "",             "foo",              ".exr.tx",  4,   NULL },
        { "foo.1-10#.bar.1-9#.bar", "foo.1-10#.bar.",   "",             "foo.1-10#.bar",    ".bar",     4,   new FrameSet("1-9") },
        { "foo.1-9.bar",            "foo.",             "",             "foo",              ".bar",     1,   new FrameSet("1-9") },
        { "foo.1-10.bar",           "foo.",             "",             "foo",              ".bar",     1,   new FrameSet("1-10") },
        { "foo.9.bar",              "foo.",             "",             "foo",              ".bar",     1,   new FrameSet("9-9") },

        { "foo.1-10#.bar",          "foo.",             "",             "foo",              ".bar",     4,   new FrameSet("1-10") },
        { "foo.1-10:10#.bar",       "foo.",             "",             "foo",              ".bar",     4,   new FrameSet("1-10:10") },
        { "/foo.1-10#.bar",         "/foo.",            "/",            "foo",              ".bar",     4,   new FrameSet("1-10") },
        { "baz/foo.1-10#.bar",      "baz/foo.",         "baz/",         "foo",              ".bar",     4,   new FrameSet("1-10") },
        { "/baz/foo.1-10#.bar",     "/baz/foo.",        "/baz/",        "foo",              ".bar",     4,   new FrameSet("1-10") },
        { "/bar/baz/foo.1-10#.bar", "/bar/baz/foo.",    "/bar/baz/",    "foo",              ".bar",     4,   new FrameSet("1-10") },

        { "foo.-15-15#.bar",        "foo.",             "",             "foo",              ".bar",     4,   new FrameSet("-15-15") },
        { "foo.-15--1#.bar",        "foo.",             "",             "foo",              ".bar",     4,   new FrameSet("-15--1") },

        { "foo.1-1000#",            "foo.",             "",             "foo",              "",         4,   new FrameSet("1-1000") },
        { "1-1000#.bar",            "",                 "",             "",                 ".bar",     4,   new FrameSet("1-1000") },
        { "1-1000#",                "",                 "",             "",                 "",         4,   new FrameSet("1-1000") },
        { "foo/1-1000#",            "foo/",             "foo/",         "",                 "",         4,   new FrameSet("1-1000") },

        { "1",                      "",                 "",             "",                 "",         1,   new FrameSet("1") },

        // Note this will no longer be expected to pass if floating-point
        // frame numbers are ever implemented.
        { "chanData.0190.5000",     "chanData.",        "",             "chanData",         ".5000",    4,   new FrameSet("190") },

        // y0 produces a FrameRange with no stepSize
        { "foo.1-10y0.bar",         "foo.",             "",             "foo",              ".bar",     1,   new FrameSet("1-10") },

        { NULL, NULL, NULL, NULL, NULL, 0, NULL },
    };

    testFileSequence(data);
}

void
FileSequenceTest::testPadSizeWithoutPadTokens()
{
    fs_test_data data[] = {
        { "foo.0009.bar",       NULL, NULL, NULL, NULL, 4, NULL },
        { "foo.1-9x0002.bar",   NULL, NULL, NULL, NULL, 1, NULL },
        { "foo.9-1x-0002.bar",  NULL, NULL, NULL, NULL, 1, NULL },
        { "foo.9-09x0002.bar",  NULL, NULL, NULL, NULL, 2, NULL },
        { "foo.9,10.bar",       NULL, NULL, NULL, NULL, 1, NULL },
        { "foo.009,10.bar",     NULL, NULL, NULL, NULL, 3, NULL },
        { "foo.-011.bar",       NULL, NULL, NULL, NULL, 4, NULL },
        { "foo.0.bar",          NULL, NULL, NULL, NULL, 1, NULL },
        { "foo.1-100:10.bar",   NULL, NULL, NULL, NULL, 1, NULL },

        { NULL, NULL, NULL, NULL, NULL, 0, NULL },
    };

    testFileSequence(data);
}

void
FileSequenceTest::testInvalidSequences()
{
    CPPUNIT_ASSERT_THROW(FileSequence(""), std::exception);

    CPPUNIT_ASSERT_THROW(FileSequence("asdasdasda"), std::exception);
    CPPUNIT_ASSERT_THROW(FileSequence("foo.fred#.bar"), std::exception);

    CPPUNIT_ASSERT_THROW(FileSequence("foo..bar"), std::exception);
    CPPUNIT_ASSERT_THROW(FileSequence("foo.-,x#.bar"), std::exception);
    CPPUNIT_ASSERT_THROW(FileSequence("foo.x2.bar"), std::exception);
    CPPUNIT_ASSERT_THROW(FileSequence("foo.-20---10.bar"), std::exception);

    // order reversed
    CPPUNIT_ASSERT_THROW(FileSequence("foo.10-1.bar"), std::exception);
    CPPUNIT_ASSERT_THROW(FileSequence("foo.-10--20.bar"), std::exception);

    // require a prefix/suffix (if a dot is present)
    CPPUNIT_ASSERT_THROW(FileSequence(".1"), std::exception);
    CPPUNIT_ASSERT_THROW(FileSequence("1."), std::exception);

    // mismatched padding
    CPPUNIT_ASSERT_THROW(FileSequence("foo.010,0020.bar"), std::exception);
    CPPUNIT_ASSERT_THROW(FileSequence("foo.010-0020.bar"), std::exception);

    // no step and colon together
    CPPUNIT_ASSERT_THROW(FileSequence("foo.1-100x2:10#.bar"), std::exception);
    CPPUNIT_ASSERT_THROW(FileSequence("foo.1-100:10x2#.bar"), std::exception);

    // no colon on non-ranges
    CPPUNIT_ASSERT_THROW(FileSequence("foo.1:10#.bar"), std::exception);

    // padding tokens in directory name
    CPPUNIT_ASSERT_THROW(
        FileSequence(
            "/net/vol240/shots/spi/home/lib/katana/katana.2.0@.75/rhel40m64/PYTHON_LIBS/NodegraphAPI/NodegraphAPI_cmodule.so"),
        std::exception);

    // a frame number that overflows 32 bit int
    CPPUNIT_ASSERT_THROW(FileSequence("569201265582281.jpg"), std::exception);
    CPPUNIT_ASSERT_THROW(FileSequence("-569201265582281.jpg"), std::exception);
    CPPUNIT_ASSERT_THROW(FileSequence("1-569201265582281.jpg"), std::exception);
    CPPUNIT_ASSERT_THROW(FileSequence("-569201265582281--1.jpg"), std::exception);
    CPPUNIT_ASSERT_THROW(FileSequence("1x569201265582281.jpg"), std::exception);
    CPPUNIT_ASSERT_THROW(FileSequence("1:569201265582281.jpg"), std::exception);
}

void
FileSequenceTest::testStringify()
{
    CPPUNIT_ASSERT_EQUAL(FileSequence("foo.011.bar")[0], std::string("foo.011.bar"));
    CPPUNIT_ASSERT_EQUAL(FileSequence("foo.-011.bar")[0], std::string("foo.-011.bar"));

    CPPUNIT_ASSERT_EQUAL(FileSequence("foo.1-10#.bar").toString(), std::string("foo.1-10#.bar"));
    CPPUNIT_ASSERT_EQUAL(FileSequence("foo.#.bar").toString(), std::string("foo.#.bar"));

    CPPUNIT_ASSERT_EQUAL(FileSequence("foo.#").toString(), std::string("foo.#"));
    CPPUNIT_ASSERT_EQUAL(FileSequence("bar/foo.#").toString(), std::string("bar/foo.#"));
    CPPUNIT_ASSERT_EQUAL(FileSequence("#.bar").toString(), std::string("#.bar"));
    CPPUNIT_ASSERT_EQUAL(FileSequence("#").toString(), std::string("#"));

    // test stingify simplifies
    CPPUNIT_ASSERT_EQUAL(FileSequence("foo.1-10x1#.bar").toString(), std::string("foo.1-10#.bar"));
    CPPUNIT_ASSERT_EQUAL(FileSequence("foo.1-10x1,2-2x0,3-3#.bar").toString(), std::string("foo.1-10,3#.bar"));
}

static void
testIter(const std::string& fsspec, const std::vector<std::string>& expected)
{
    FileSequence fs = FileSequence(fsspec);

    std::vector<std::string> r;
    FileSequence::iterator iter = fs.begin();
    for (; iter != fs.end(); ++iter) {
        r.push_back(*iter);
    }

    std::stringstream errmsg;
    errmsg << fsspec << " by iteration, expected '";
    std::copy(expected.begin(), expected.end(), std::ostream_iterator<std::string>(errmsg, " "));
    errmsg << "' got '";
    std::copy(r.begin(), r.end(), std::ostream_iterator<std::string>(errmsg, " "));
    errmsg << "'";
    std::string e = errmsg.str();
    CPPUNIT_ASSERT_MESSAGE(e.c_str(), expected == r);
}

void
FileSequenceTest::testIter()
{
    std::vector<std::string> A(5);
    A[0] = "foo.0001.bar";
    A[1] = "foo.0002.bar";
    A[2] = "foo.0003.bar";
    A[3] = "foo.0004.bar";
    A[4] = "foo.0005.bar";
    ::testIter("foo.1-5#.bar", A);
}

void
FileSequenceTest::testContains()
{
    // Simple test that FileSequence passes "contains" test through
    // to FrameSet.
    FileSequence fs = FileSequence("foo.1-10#.bar");
    CPPUNIT_ASSERT(fs.contains(1, NULL));
    CPPUNIT_ASSERT(!fs.contains(0, NULL));
}

static void
testCompare(const std::string& fsspec1, const std::string& fsspec2, bool expected)
{
    FileSequence fs1 = FileSequence(fsspec1);
    FileSequence fs2 = FileSequence(fsspec2);
    bool equal = fs1 == fs2;
    bool not_equal = fs1 != fs2;
    {
        std::stringstream errmsg;
        errmsg << "Comparing '" << fsspec1 << "' == '" << fsspec2 << "'";
        errmsg << " Expected '" << expected << "'";
        std::string e = errmsg.str();
        CPPUNIT_ASSERT_MESSAGE(e, equal == expected);
    }
    {
        std::stringstream errmsg;
        errmsg << "Comparing '" << fsspec1 << "' != '" << fsspec2 << "'";
        errmsg << " Expected '" << !expected << "'";
        std::string e = errmsg.str();
        CPPUNIT_ASSERT_MESSAGE(e, not_equal != expected);
    }
}

void
FileSequenceTest::testCompare()
{
    ::testCompare("foo.1-10#.bar", "foo.1-10#.bar", true);
    ::testCompare("foo.1-10#.bar", "foo.1-10#.baz", false);

    ::testCompare("foo.1-10@#.bar", "foo.1-10#@.bar", true);

    ::testCompare("foo.1-10#.bar", "foo.1-10#@.bar", false);

    ::testCompare("foo.1-10#.bar", "baz.1-10#.bar", false);
    ::testCompare("foo.1-10#.bar", "baz.2-10#.bar", false);
}

void
FileSequenceTest::testProceduralFileSequence()
{
    FrameSet frameSet = FrameSet("1-10", 4);
    FileSequence fs = FileSequence("baz/foo.", frameSet, ".bar");
    CPPUNIT_ASSERT(fs == FileSequence("baz/foo.1-10#.bar"));
    // dirname and basename must be computed from prefix
    CPPUNIT_ASSERT(fs.getDirname() == "baz/");
    CPPUNIT_ASSERT(fs.getBasename() == "foo");

    // setSuffix requires a leading dot
    CPPUNIT_ASSERT_THROW(fs.setSuffix("suffix"), std::exception);

    // setSuffix allows empty string
    fs.setSuffix("");
    CPPUNIT_ASSERT_EQUAL_MESSAGE("suffix is empty", std::string(""),
                                 fs.getSuffix());

    // setPrefix requires a trailing dot
    CPPUNIT_ASSERT_THROW(fs.setPrefix("baz/foo"), std::exception);

    // setBasename rejects any slashes
    CPPUNIT_ASSERT_THROW(fs.setBasename("baz/foo"), std::exception);

    // setBasename does not require a trailing dot
    fs.setBasename("basename");

    // prefix has a trailing dot after setBasename
    CPPUNIT_ASSERT_EQUAL_MESSAGE("prefix wrong after setBasename",
                                 std::string("baz/basename."),
                                 fs.getPrefix());

    fs.setDirname("dirname/");

    // prefix has a trailing dot after setDirname
    CPPUNIT_ASSERT_EQUAL_MESSAGE("prefix wrong after setDirname",
                                 std::string("dirname/basename."),
                                 fs.getPrefix());

    char spec[] = "basename.1#.bar";

    FileSequence fs1 = FileSequence();
    fs1.setSequence(spec);

    FileSequence fs2 = FileSequence(spec);
    CPPUNIT_ASSERT_EQUAL_MESSAGE("getBasename same for constructor vs setSequence",
                                 fs1.getBasename(), fs2.getBasename());
}

static void
testMerge(const std::string& fsone, const std::string& fstwo, const std::string& expected)
{
    FileSequence fs1 = FileSequence(fsone);
    FileSequence fs2 = FileSequence(fstwo);

    fs1.merge(fs2);

    std::stringstream merged;
    merged << expected << " == " << fsone << " <- " << fstwo;

    CPPUNIT_ASSERT_EQUAL_MESSAGE(merged.str(), expected, fs1.toString());
}

void
FileSequenceTest::testMerge()
{
    ::testMerge("foo.1#.jpg", "foo.2#.jpg", "foo.1-2#.jpg");
    ::testMerge("foo.#.jpg", "foo.1#.jpg", "foo.#.jpg");
    ::testMerge("foo.1#.jpg", "foo.#.jpg", "foo.#.jpg");

    // these should merge
    ::testMerge("foo.0001.jpg", "foo.1000.jpg", "foo.1,1000#.jpg");
    ::testMerge("foo.1000.jpg", "foo.0001.jpg", "foo.1,1000#.jpg");

    ::testMerge("foo.0001.jpg", "foo.10000.jpg", "foo.1,10000#.jpg");
    ::testMerge("foo.10000.jpg", "foo.0001.jpg", "foo.1,10000#.jpg");

    // these shouldn't merge
    CPPUNIT_ASSERT_THROW(::testMerge("foo.01.jpg", "foo.001.jpg", ""), std::exception);
}

struct fr_test_data {
    const char *fr;
    const int inTime;
    const int outTime;
    const int stepSize;
};

static void
testFrameRange(const fr_test_data* data)
{
    const fr_test_data* d = data;
    int i = 0;

    while (d->fr) {
        ++i;

        FrameRange fr = FrameRange(d->fr);

        {
            std::stringstream errmsg;
            errmsg << "Test index " << i << ", fr '" << d->fr << "'";
            errmsg << " Expected inTime '" << d->inTime << "', got '" << fr.inTime << "'";
            std::string e = errmsg.str();
            CPPUNIT_ASSERT_MESSAGE(e.c_str(), fr.inTime == d->inTime);
        }
        {
            std::stringstream errmsg;
            errmsg << "Test index " << i << ", fr '" << d->fr << "'";
            errmsg << " Expected outTime '" << d->outTime << "', got '" << fr.outTime << "'";
            std::string e = errmsg.str();
            CPPUNIT_ASSERT_MESSAGE(e.c_str(), fr.outTime == d->outTime);
        }
        {
            std::stringstream errmsg;
            errmsg << "Test index " << i << ", fr '" << d->fr << "'";
            errmsg << " Expected stepSize '" << d->stepSize << "', got '" << fr.stepSize << "'";
            std::string e = errmsg.str();
            CPPUNIT_ASSERT_MESSAGE(e.c_str(), fr.stepSize == d->stepSize);
        }

        ++d;
    }
}


void
FrameRangeTest::testVariousFrameRanges()
{
    fr_test_data data[] = {
        { "1",          1,  1,  1 },
        { "10",         10, 10, 1 },
        { "1-7",        1,  7,  1 },
        { "15-19",      15, 19, 1 },
        { "1-1x1",      1,  1,  1 },
        { "1-7x8",      1,  7,  8 },
        { "15-1x-2",    15, 1,  -2 },

        { NULL,         0,  0,  0 },
    };

    testFrameRange(data);
}

void
FrameRangeTest::testInvalidFrameRanges()
{
    CPPUNIT_ASSERT_THROW(FrameRange("19-15"), std::exception);
    CPPUNIT_ASSERT_THROW(FrameRange("asdasda"), std::exception);
    CPPUNIT_ASSERT_THROW(FrameRange("7-1x1"), std::exception);
    CPPUNIT_ASSERT_THROW(FrameRange("1-15x-1"), std::exception);
}

static void
testContains(const std::string& frspec, const std::vector<int>& expected)
{
    FrameRange fr = FrameRange(frspec);

    // via contains
    std::vector<int>::const_iterator iter = expected.begin();
    for (; iter != expected.end(); ++iter) {
        std::stringstream errmsg;
        errmsg << frspec << " by contains, expected '" << *iter << "'";
        std::string e = errmsg.str();
        CPPUNIT_ASSERT_MESSAGE(e.c_str(), fr.contains(*iter, NULL));
    }

    // via iteration
    std::vector<int> r;
    FrameRange::iterator iter2 = fr.begin();
    for (; iter2 != fr.end(); ++iter2) {
        r.push_back(*iter2);
    }

    std::stringstream errmsg;
    errmsg << frspec << " by iteration, expected '";
    std::copy(expected.begin(), expected.end(), std::ostream_iterator<int>(errmsg, " "));
    errmsg << "' got '";
    std::copy(r.begin(), r.end(), std::ostream_iterator<int>(errmsg, " "));
    errmsg << "'";
    std::string e = errmsg.str();
    CPPUNIT_ASSERT_MESSAGE(e.c_str(), expected == r);
}

void
FrameRangeTest::testFrameRangeContainsAndIter()
{
    std::vector<int> A(10);
    A[0] = 1;
    A[1] = 2;
    A[2] = 3;
    A[3] = 4;
    A[4] = 5;
    A[5] = 6;
    A[6] = 7;
    A[7] = 8;
    A[8] = 9;
    A[9] = 10;
    testContains("1-10",     A);

    std::vector<int> B(5);
    B[0] = 1;
    B[1] = 3;
    B[2] = 5;
    B[3] = 7;
    B[4] = 9;
    testContains("1-10x2",   B);

    std::vector<int> C(10);
    C[0] = 10;
    C[1] = 9;
    C[2] = 8;
    C[3] = 7;
    C[4] = 6;
    C[5] = 5;
    C[6] = 4;
    C[7] = 3;
    C[8] = 2;
    C[9] = 1;
    testContains("10-1x-1",  C);

    std::vector<int> D(5);
    D[0] = 20;
    D[1] = 18;
    D[2] = 16;
    D[3] = 14;
    D[4] = 12;
    testContains("20-12x-2", D);

    std::vector<int> E(10);
    E[0] = 1;
    E[1] = 6;
    E[2] = 3;
    E[3] = 5;
    E[4] = 7;
    E[5] = 9;
    E[6] = 2;
    E[7] = 4;
    E[8] = 8;
    E[9] = 10;
    testContains("1-10:5", E);

    std::vector<int> F(5);
    F[0] = 2;
    F[1] = 4;
    F[2] = 6;
    F[3] = 8;
    F[4] = 10;
    testContains("1-10y2", F);

    std::vector<int> G(6);
    G[0] = 2;
    G[1] = 3;
    G[2] = 5;
    G[3] = 6;
    G[4] = 8;
    G[5] = 9;
    testContains("1-10y3", G);

    std::vector<int> H(6);
    H[0] = 9;
    H[1] = 8;
    H[2] = 6;
    H[3] = 5;
    H[4] = 3;
    H[5] = 2;
    testContains("10-1y-3", H);
}

void
FrameRangeTest::testIsSequence()
{
    CPPUNIT_ASSERT_EQUAL_MESSAGE("1001 is a FrameRange",    FrameRange::isSequence("1001"), true);
    CPPUNIT_ASSERT_EQUAL_MESSAGE("10+12 is not a FrameRange",    FrameRange::isSequence("10+12"), false);
    CPPUNIT_ASSERT_EQUAL_MESSAGE("abc is not a FrameRange",    FrameRange::isSequence("abc"), false);
}

static void
testContainsIndex(const std::string& frspec, int frame, int expected_index)
{
    FrameRange fr = FrameRange(frspec);

    int index;
    fr.contains(frame, &index);

    std::stringstream errmsg;
    errmsg << "FrameRange " << frspec << " index of " << frame;
    std::string e = errmsg.str();

    CPPUNIT_ASSERT_EQUAL_MESSAGE(e.c_str(), expected_index, index);
}

void
FrameRangeTest::testContainsIndex()
{
    ::testContainsIndex("1-10", 1, 0);
    ::testContainsIndex("1-10x2", 3, 1);

    ::testContainsIndex("1-10y2", 2, 0);
    ::testContainsIndex("1-10y2", 4, 1);
    ::testContainsIndex("1-10y2", 6, 2);

    ::testContainsIndex("1-10y3", 2, 0);
    ::testContainsIndex("1-10y3", 3, 1);
    ::testContainsIndex("1-10y3", 5, 2);
    ::testContainsIndex("1-10y3", 6, 3);
    ::testContainsIndex("1-10y3", 8, 4);
    ::testContainsIndex("1-10y3", 9, 5);

    ::testContainsIndex("1-10y4", 2, 0);
    ::testContainsIndex("1-10y4", 3, 1);
    ::testContainsIndex("1-10y4", 4, 2);
    ::testContainsIndex("1-10y4", 6, 3);
    ::testContainsIndex("1-10y4", 7, 4);
    ::testContainsIndex("1-10y4", 8, 5);
    ::testContainsIndex("1-10y4", 10, 6);

    ::testContainsIndex("10-1y-4", 9, 0);
    ::testContainsIndex("10-1y-4", 8, 1);
    ::testContainsIndex("10-1y-4", 7, 2);
    ::testContainsIndex("10-1y-4", 5, 3);
    ::testContainsIndex("10-1y-4", 4, 4);
    ::testContainsIndex("10-1y-4", 3, 5);
    ::testContainsIndex("10-1y-4", 1, 6);
}

static void
testFrameSet(const std::string& fsspec, std::set<int> expected)
{
    FrameSet fs = FrameSet(fsspec);
    std::set<int> r;
    FrameSet::iterator iter = fs.begin();
    for (; iter != fs.end(); ++iter) {
        r.insert(*iter);
    }

    std::stringstream errmsg;
    errmsg << fsspec << ", expected '";
    std::copy(expected.begin(), expected.end(), std::ostream_iterator<int>(errmsg, " "));
    errmsg << "' got '";
    std::copy(r.begin(), r.end(), std::ostream_iterator<int>(errmsg, " "));
    errmsg << "'";
    std::string e = errmsg.str();
    CPPUNIT_ASSERT_MESSAGE(e.c_str(), expected == r);
}

void
FrameSetTest::testVariousFrameSets()
{
    std::set<int> A;
    A.insert(1);
    testFrameSet("1", A);

    std::set<int> B;
    B.insert(1);
    B.insert(2);
    testFrameSet("1-2", B);
    testFrameSet("1,2", B);

    std::set<int> C;
    C.insert(1);
    C.insert(3);
    C.insert(5);
    C.insert(9);
    C.insert(15);
    testFrameSet("1-4x2,5,9,15", C);
}

void
FrameSetTest::testInvalidFrameSets()
{
    CPPUNIT_ASSERT_THROW(FrameSet("asbasdas"), std::exception);
}

static void
testNearest(const std::string& fsspec, int target, bool has_left, int left, bool has_right, int right)
{
    FrameSet fs = FrameSet(fsspec);

    bool rhasl, rhasr;
    int rl, rr;
    fs.nearest(target, &rhasl, &rl, &rhasr, &rr);

    std::stringstream errmsg;
    errmsg << fsspec << ", target '" << target << "', ";

    std::string e = errmsg.str() + " has left";
    CPPUNIT_ASSERT_EQUAL_MESSAGE(e.c_str(), has_left, rhasl);
    if (rhasl) {
        e = errmsg.str() + " left value";
        CPPUNIT_ASSERT_EQUAL_MESSAGE(e.c_str(), left, rl);
    }

    e = errmsg.str() + " has right";
    CPPUNIT_ASSERT_EQUAL_MESSAGE(e.c_str(), has_right, rhasr);
    if (rhasr) {
        e = errmsg.str() + " right value";
        CPPUNIT_ASSERT_EQUAL_MESSAGE(e.c_str(), right, rr);
    }
}

void
FrameSetTest::testNearest()
{
    ::testNearest("1,3", 2, true, 1, true, 3);
    ::testNearest("1,3", 1, false, 0, true, 3);
    ::testNearest("1,3", 3, true, 1, false, 0);
    ::testNearest("1,2,3", 2, true, 1, true, 3);
    ::testNearest("2", 2, false, 0, false, 0);
    ::testNearest("1-7", 4, true, 3, true, 5);
    ::testNearest("7-1x-1", 4, true, 3, true, 5);
    ::testNearest("1-7x2", 4, true, 3, true, 5);
    ::testNearest("7-1x-2", 4, true, 3, true, 5);
    ::testNearest("1-7x14", 4, true, 1, false, 0);
    ::testNearest("13-23x4", 19, true, 17, true, 21);
    ::testNearest("13-20x4", 19, true, 17, false, 0);
    ::testNearest("13-20x4", 1, false, 0, true, 13);
    ::testNearest("13-20x4", 13, false, 0, true, 17);
    ::testNearest("1-10y3", 3, true, 2, true, 5);
    ::testNearest("1-10y3", 11, true, 9, false, 0);
    ::testNearest("2-10y3", 1, false, 0, true, 3);
    ::testNearest("10-1y-3", 1, false, 0, true, 2);
    ::testNearest("10-1y-3", 3, true, 2, true, 5);
}

static void
testNormalize(const std::string& fsspec, const std::string& expected)
{
    FrameSet fs = FrameSet(fsspec);
    fs.normalize();

    std::stringstream normalized;
    normalized << fs;

    CPPUNIT_ASSERT_EQUAL_MESSAGE(fsspec.c_str(), expected, normalized.str());
}

void
FrameSetTest::testNormalize()
{
        // trivial cases
        ::testNormalize("","");
        ::testNormalize("1","1");
        ::testNormalize("1-3","1-3");

        // prefer 1,2 over 1-2
        ::testNormalize("1-2","1,2");
        ::testNormalize("1-3x2","1,3");

        // original order is lost!
        ::testNormalize("3-1x-1","1-3");

        // duplicates are pruned
        ::testNormalize("1-2,2-3","1-3");

        // detect steps
        ::testNormalize("1,3,5,7","1-7x2");
        ::testNormalize("1-3x2,5-7x2","1-7x2");
        ::testNormalize("1,2,4,8,12,16,17,18", "1,2,4-16x4,17,18");

        // prefer to put 16 in the first range because it would be longer
        // [matches seqls: 1,2,4-16x4,17-19]
        ::testNormalize("1,2,4,8,12,16,17,18,19", "1,2,4-16x4,17-19");
        // prefer to put 16 in the second range because it would be longer
        // [deviates from seqls: 1,2,4-16x4,17-20]
        ::testNormalize("1,2,4,8,12,16,17,18,19,20", "1,2,4-12x4,16-20");

        // prefer to put 10 in the first range because it makes the
        // range with the higher skip longer (tie breaker)
        // [matches seqls: 1-10x3,12-16x2]
        ::testNormalize("1,4,7,10,12,14,16", "1-10x3,12-16x2");
        // prefer to put 6 in the second range because it makes the
        // range with the higher skip longer (tie breaker)
        // [deviates from seqls: 1-7x2,10-16x3]
        ::testNormalize("1,3,5,7,10,13,16", "1-5x2,7-16x3");
        // frames at the end affect multiple other sequences chosen
        ::testNormalize("1,3,5,10,15,16,17,18", "1-5x2,10,15-18");

        ::testNormalize("1-639,641,643,645,647,649,651-1000", "1-639,641-649x2,651-1000");
}

static void
testIndex(const std::string& fsspec, int elem, int expected)
{
    FrameSet fs = FrameSet(fsspec);
    int i = fs.index(elem);

    std::stringstream errmsg;
    errmsg << fsspec << ", elem '" << elem << "'";
    std::string e = errmsg.str();
    CPPUNIT_ASSERT_EQUAL_MESSAGE(e.c_str(), expected, i);
}

void
FrameSetTest::testIndex()
{
    ::testIndex("1,3", 1, 0);
    ::testIndex("1,3", 2, -1);
    ::testIndex("1,3", 3, 1);
    ::testIndex("1-10,12-20", 12, 10);
    ::testIndex("1-10,12-20", 13, 11);

    // 1 3 5 7 9 12 14 16 18 20
    // 0 1 2 3 4  5  6  7  8  9
    ::testIndex("1-10x2,12-20x2", 12, 5);
    ::testIndex("1-10x2,12-20x2", 14, 6);
    ::testIndex("1-10x2,12-20x2", 16, 7);
    ::testIndex("1-10x2,12-20x2", 18, 8);
    ::testIndex("1-10x2,12-20x2", 20, 9);

    // 1 3 5 7 9 20 18 16 14 12
    // 0 1 2 3 4  5  6  7  8  9
    ::testIndex("1-10x2,20-12x-2", 12, 9);
    ::testIndex("1-10x2,20-12x-2", 14, 8);
    ::testIndex("1-10x2,20-12x-2", 16, 7);
    ::testIndex("1-10x2,20-12x-2", 18, 6);
    ::testIndex("1-10x2,20-12x-2", 20, 5);

    // 1 11 21 31 36 37
    // 0  1  2  3  4  5
    ::testIndex("1-35x10,36-37", 1, 0);
    ::testIndex("1-35x10,36-37", 11, 1);
    ::testIndex("1-35x10,36-37", 21, 2);
    ::testIndex("1-35x10,36-37", 31, 3);
    ::testIndex("1-35x10,36-37", 32, -1);
    ::testIndex("1-35x10,36-37", 36, 4);
    ::testIndex("1-35x10,36-37", 37, 5);
}

static void
testRevIndex(const std::string& fsspec, int index, int expected)
{
    FrameSet fs = FrameSet(fsspec);
    int elem = fs[index];

    std::stringstream errmsg;
    errmsg << fsspec << ", index '" << index << "'";
    std::string e = errmsg.str();
    CPPUNIT_ASSERT_EQUAL_MESSAGE(e.c_str(), expected, elem);
}

void
FrameSetTest::testRevIndex()
{
    ::testRevIndex("1-3", 0, 1);
    ::testRevIndex("1-3", 1, 2);
    ::testRevIndex("1-3", 2, 3);
    ::testRevIndex("1-3", -1, 3);
    ::testRevIndex("1-3", -2, 2);
    ::testRevIndex("1-3", -3, 1);

    ::testRevIndex("1,3", 0, 1);
    ::testRevIndex("1,3", 1, 3);
    ::testRevIndex("1,3", -1, 3);
    ::testRevIndex("1,3", -2, 1);
}

static void
testInvalidRevIndex(const std::string& fsspec, int index)
{
    FrameSet fs = FrameSet(fsspec);
    CPPUNIT_ASSERT_THROW(fs[index], std::exception);
}

void
FrameSetTest::testInvalidRevIndex()
{
    ::testInvalidRevIndex("1-3", -4);
    ::testInvalidRevIndex("1-3", 3);
}

static void
testLen(const std::string& fsspec, int expected)
{
    FrameSet fs = FrameSet(fsspec);
    int length = fs.size();

    CPPUNIT_ASSERT_EQUAL_MESSAGE(fsspec.c_str(), expected, length);
}

void
FrameSetTest::testLen()
{
    ::testLen("1", 1);
    ::testLen("1-10", 10);
    ::testLen("1,2", 2);
    ::testLen("1-10x2", 5);
}

static void
testFrameSetCompare(const std::string& fsspec1, const std::string& fsspec2, bool expected)
{
    FrameSet fs1 = FrameSet(fsspec1);
    FrameSet fs2 = FrameSet(fsspec2);
    bool equal = fs1 == fs2;
    bool not_equal = fs1 != fs2;
    {
        std::stringstream errmsg;
        errmsg << "Comparing '" << fsspec1 << "' == '" << fsspec2 << "'";
        errmsg << " Expected '" << expected << "'";
        std::string e = errmsg.str();
        CPPUNIT_ASSERT_MESSAGE(e, equal == expected);
    }
    {
        std::stringstream errmsg;
        errmsg << "Comparing '" << fsspec1 << "' != '" << fsspec2 << "'";
        errmsg << " Expected '" << !expected << "'";
        std::string e = errmsg.str();
        CPPUNIT_ASSERT_MESSAGE(e, not_equal != expected);
    }
}

void
FrameSetTest::testCompare()
{
    ::testFrameSetCompare("1-10", "1-10", true);
    ::testFrameSetCompare("1-10", "2-11", false);
}

void
FrameSetTest::testIsSequence()
{
    CPPUNIT_ASSERT_EQUAL_MESSAGE("101 is a FrameSet",   FrameSet::isSequence("101"),    true);
    CPPUNIT_ASSERT_EQUAL_MESSAGE("1001 is a FrameSet",  FrameSet::isSequence("1001"),   true);
    CPPUNIT_ASSERT_EQUAL_MESSAGE("abc is not FrameSet", FrameSet::isSequence("abc"),    false);
    CPPUNIT_ASSERT_EQUAL_MESSAGE("18? is not FrameSet", FrameSet::isSequence("18?"),    false);
}

static std::ostream&
operator<<(std::ostream& os, const std::vector<FileSequence>& fses)
{
    os << "[";
    std::copy(fses.begin(), fses.end(), std::ostream_iterator<FileSequence>(os, ", "));
    os << "]";
    return os;
}

static std::ostream&
operator<<(std::ostream& os, const std::vector<std::string>& strs)
{
    os << "[";
    std::copy(strs.begin(), strs.end(), std::ostream_iterator<std::string>(os, ", "));
    os << "]";
    return os;
}

static void
testFindSequence(
    const std::vector<std::string>& input,
    const std::vector<FileSequence>& expected_seqs,
    const std::vector<std::string>& expected_nonseqs)
{
    std::vector<FileSequence> seqs;
    std::vector<std::string> nonseqs;

    FindSequence(input, seqs, nonseqs);

    CPPUNIT_ASSERT_EQUAL(expected_seqs, seqs);
    CPPUNIT_ASSERT_EQUAL(expected_nonseqs, nonseqs);
}

void
FindSequenceTest::testFindSequence()
{
    std::vector<std::string> input;
    std::vector<FileSequence> expected_seqs;
    std::vector<std::string> expected_nonseqs;

    // ===================================================================== //

    input.clear(); expected_seqs.clear(); expected_nonseqs.clear();

    input.push_back("foo.0001.bar");
    input.push_back("foo.0002.bar");
    input.push_back("foo.0003.bar");

    expected_seqs.push_back(FileSequence("foo.1-3#.bar"));

    ::testFindSequence(input, expected_seqs, expected_nonseqs);

    // ===================================================================== //

    input.clear(); expected_seqs.clear(); expected_nonseqs.clear();

    input.push_back("asldkfgj");

    expected_nonseqs.push_back("asldkfgj");

    ::testFindSequence(input, expected_seqs, expected_nonseqs);

    // ===================================================================== //

    input.clear(); expected_seqs.clear(); expected_nonseqs.clear();

    input.push_back("foo.0001.bar");
    input.push_back("bar.0002.baz");
    input.push_back("foo.0003.bar");
    input.push_back("bar.0004.baz");
    input.push_back("foo.0005.bar");
    input.push_back("bar.0006.baz");

    expected_seqs.push_back(FileSequence("bar.2-6x2#.baz"));
    expected_seqs.push_back(FileSequence("foo.1-5x2#.bar"));

    ::testFindSequence(input, expected_seqs, expected_nonseqs);

    // ===================================================================== //

    input.clear(); expected_seqs.clear(); expected_nonseqs.clear();

    input.push_back("foo.101-200.bar");

    expected_nonseqs.push_back("foo.101-200.bar");

    ::testFindSequence(input, expected_seqs, expected_nonseqs);
}

void
FindSequenceTest::profileFindSequenceOnDisk()
{
    std::string path("test/test_files/FindSequenceOnDisk_test1");

    //1205 files
    //seqls 0:00.62
    //python bindings to FileSequence 0:23.05
    // /shots/clo/xxx07/geometry/components/manny/cmpt/v12/geometry/manny_hi/pit/scene.pit_d/bgeo
    //contains: dynamic.101-701#.bgeo, dynamic.101-701#.bgtoc,
    //          static.bgeo, static.bgtoc

    std::vector<FileSequence> expected_seqs;
    std::vector<std::string> expected_nonseqs;

    FindSequenceOnDisk(path, expected_seqs, expected_nonseqs, false, false);
}

void
PaddingTest::testCheckString()
{
    CPPUNIT_ASSERT_EQUAL(Padding::checkString("1"), true);
    CPPUNIT_ASSERT_EQUAL(Padding::checkString("-1"), true);
    CPPUNIT_ASSERT_EQUAL(Padding::checkString("001"), true);
    CPPUNIT_ASSERT_EQUAL(Padding::checkString("-001"), true);
    CPPUNIT_ASSERT_EQUAL(Padding::checkString("1001"), true);

    // Padding rejects a lone minus or an empty string,
    //  but doesn't actually care about non-numbers.
    CPPUNIT_ASSERT_EQUAL(Padding::checkString(""), false);
    CPPUNIT_ASSERT_EQUAL(Padding::checkString("-"), false);
}

void
PaddingTest::testFromString()
{
    CPPUNIT_ASSERT_EQUAL(Padding(false, 1), Padding::fromString("1"));
    CPPUNIT_ASSERT_EQUAL(Padding(true, 3), Padding::fromString("001"));
    CPPUNIT_ASSERT_EQUAL(Padding(false, 1), Padding::fromString("0"));
    CPPUNIT_ASSERT_EQUAL(Padding(false, 2), Padding::fromString("-0"));
}

void
PaddingTest::testOperatorBitwiseAnd()
{
    Padding a = Padding::fromString("009");
    Padding b = Padding::fromString("10");

    CPPUNIT_ASSERT_EQUAL(a, a & b);
    CPPUNIT_ASSERT_EQUAL(a, b & a);

    Padding c = Padding::fromString("0001");
    Padding d = Padding::fromString("0002");

    CPPUNIT_ASSERT_EQUAL(c, c & d);
    CPPUNIT_ASSERT_EQUAL(c, d & c);
    CPPUNIT_ASSERT_EQUAL(d, c & d);
    CPPUNIT_ASSERT_EQUAL(d, d & c);

    Padding e = Padding::fromString("1000");
    Padding f = Padding::fromString("100");

    CPPUNIT_ASSERT_EQUAL(f, e & f);
    CPPUNIT_ASSERT_EQUAL(f, f & e);
}
