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


#include <cppunit/extensions/TestFactoryRegistry.h>
#include <cppunit/CompilerOutputter.h>
#include <cppunit/TestResult.h>
#include <cppunit/TestResultCollector.h>
#include <cppunit/TestRunner.h>
#include <cppunit/TextTestProgressListener.h>

#include <stdexcept>

#include "FileSequenceTest.h"

int
main(int argc, char *argv[])
{
    std::string testPath = (argc > 1) ? std::string(argv[1]) : "";

    // Create the event manager and test controller
    CppUnit::TestResult controller;

    // Add a listener that collects test result
    CppUnit::TestResultCollector result;
    controller.addListener(&result);

    // Add a listener that print dots as test run.
    CppUnit::TextTestProgressListener progress;
    controller.addListener(&progress);

    // Add the top suite to the test runner
    CppUnit::TestRunner runner;
    runner.addTest(CppUnit::TestFactoryRegistry::getRegistry().makeTest());
    try {
        std::cerr << "Running " << testPath;
        runner.run(controller, testPath);

        std::cerr << std::endl;

        // Print test in a compiler compatible format.
        CppUnit::CompilerOutputter outputter(&result, std::cerr);
        outputter.write();
    }
    catch (std::invalid_argument &e)  // Test path not resolved
    {
        std::cerr << std::endl
                  << "ERROR: "  << e.what()
                  << std::endl;

        return 1;
    }

    return result.wasSuccessful() ? 0 : 1;
}
