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


#include <cppunit/extensions/HelperMacros.h>

class FileSequenceTest : public CppUnit::TestFixture {

public:

    CPPUNIT_TEST_SUITE(FileSequenceTest);
    CPPUNIT_TEST(testVariousFileSequences);
    CPPUNIT_TEST(testPadSizeWithoutPadTokens);
    CPPUNIT_TEST(testInvalidSequences);
    CPPUNIT_TEST(testStringify);
    CPPUNIT_TEST(testContains);
    CPPUNIT_TEST(testIter);
    CPPUNIT_TEST(testCompare);
    CPPUNIT_TEST(testProceduralFileSequence);
    CPPUNIT_TEST(testMerge);
    CPPUNIT_TEST_SUITE_END();

    void testVariousFileSequences();
    void testPadSizeWithoutPadTokens();
    void testInvalidSequences();
    void testStringify();
    void testContains();
    void testIter();
    void testCompare();
    void testProceduralFileSequence();
    void testMerge();
};

class FrameRangeTest : public CppUnit::TestFixture {

public:

    CPPUNIT_TEST_SUITE(FrameRangeTest);
    CPPUNIT_TEST(testVariousFrameRanges);
    CPPUNIT_TEST(testInvalidFrameRanges);
    CPPUNIT_TEST(testFrameRangeContainsAndIter);
    CPPUNIT_TEST(testIsSequence);
    CPPUNIT_TEST(testContainsIndex);
    CPPUNIT_TEST_SUITE_END();

    void testVariousFrameRanges();
    void testInvalidFrameRanges();
    void testFrameRangeContainsAndIter();
    void testIsSequence();
    void testContainsIndex();
};

class FrameSetTest : public CppUnit::TestFixture {

public:

    CPPUNIT_TEST_SUITE(FrameSetTest);
    CPPUNIT_TEST(testVariousFrameSets);
    CPPUNIT_TEST(testInvalidFrameSets);
    CPPUNIT_TEST(testNearest);
    CPPUNIT_TEST(testNormalize);
    CPPUNIT_TEST(testIndex);
    CPPUNIT_TEST(testRevIndex);
    CPPUNIT_TEST(testInvalidRevIndex);
    CPPUNIT_TEST(testLen);
    CPPUNIT_TEST(testCompare);
    CPPUNIT_TEST(testIsSequence);
    CPPUNIT_TEST_SUITE_END();

    void testVariousFrameSets();
    void testInvalidFrameSets();
    void testNearest();
    void testNormalize();
    void testIndex();
    void testRevIndex();
    void testInvalidRevIndex();
    void testLen();
    void testCompare();
    void testIsSequence();
};

class FindSequenceTest : public CppUnit::TestFixture {

public:

    CPPUNIT_TEST_SUITE(FindSequenceTest);
#ifdef PROFILING
    CPPUNIT_TEST(profileFindSequenceOnDisk);
#else
    CPPUNIT_TEST(testFindSequence);
#endif
    CPPUNIT_TEST_SUITE_END();

    void testFindSequence();
    void profileFindSequenceOnDisk();
};

class PaddingTest : public CppUnit::TestFixture {

public:

    CPPUNIT_TEST_SUITE(PaddingTest);
    CPPUNIT_TEST(testCheckString);
    CPPUNIT_TEST(testFromString);
    CPPUNIT_TEST(testOperatorBitwiseAnd);
    CPPUNIT_TEST_SUITE_END();

    void testCheckString();
    void testFromString();
    void testOperatorBitwiseAnd();
};
