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


#ifndef SPI_EXCEPTIONS_ICE
#define SPI_EXCEPTIONS_ICE

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
 **/

/*
 * $HeadURL$
 * $LastChangedDate$
 * $LastChangedBy$
 * $LastChangedRevision$
 */

#include <spi_types.ice>

[["java:package:com.imageworks.common"]]
[["python:package:spi"]]
module SpiIce
{
    /**
     * Exceptions.
     *
     * Ice applications need exception instances in two different use
     * cases.

     * The first is for methods that operate on a single server side
     * object that throws an exception to indicate a fault, such as
     * attempting to find an object that does not exist.
     *
     * The second is to return from batch methods that operate on
     * multiple server side objects where it is inappropriate to
     * throw an exception for a fault in the operation on any one
     * object, for example, looking up two or more objects.  In this
     * case, the batch method should return an array of results, where
     * each array element includes exception information for a fault
     * in that one operation.
     *
     * Because not all languages support throwing arbitrary classes,
     * take Java for example, where exception classes must derive from
     * Throwable, Ice exceptions cannot be used as structures and
     * structures cannot be used as Ice exceptions.  To handle the two
     * use cases for single and multiple operations, two separate Ice
     * constructs must be created to store the exception information.
     * An Ice "exception" must be used for thrown exceptions, and an
     * Ice "struct" exception must be used for returned exceptions,
     * these are named SpiIceException and SpiIceCause respectively.
     * Both a SpiIceException and a SpiIceCause contain a string
     * message and a stack trace.
     *
     * One additional requirement is to support exception chaining.
     * Exception chaining is provided in Java, where one Throwable has
     * a potentially non-null reference to another Throwable that was
     * the cause of the exception.  The chains can be of any length.
     *
     * There are a few reasons to do this, but the most important one
     * is that this allows an API to provide a set of exception
     * classes specific to the API that hide implementation specific
     * exceptions that may occur, but still provide the cause
     * exception to the client to aid in debugging.  More information
     * may be found here.
     *
     * http://java.sun.com/j2se/1.5.0/docs/api/java/lang/Throwable.html
     *
     * Here, Java exceptions are emulated with a few differences:
     *
     * 1) Java chaining is implemented as a linked list.  However,
     *    because Ice exceptions are not structures and cannot contain
     *    a field that points to or references to another instance of
     *    the same Ice exception "class", exception chains are
     *    represented here as a sequence of SpiIceCause, where each
     *    SpiIceCause contains one message and one stack trace.
     *
     * 2) The stack trace in Java is an array of StackTraceElement's.
     *    Here, the stack trace is an array of strings, where a single
     *    element contains the source filename and line number.
     *
     * 3) The main exception structure is named SpiIceException so
     *    that the server and client side code can use the name
     *    SpiException.
     **/

    /**
     * This structure provides the information for a single cause, the
     * message and a stack trace.
     **/
    struct SpiIceCause {
        string message;
        StringSeq stackTrace;
    };

    /**
     * A list of causes.
     *
     * For the Java Ice cause sequence, the sequence is represented as
     * a java.util.ArrayList and is done so that an
     * java.util.ArrayList can be allocated with a large enough size
     * to hold most exception chains and not have to be reallocated
     * when additional exceptions are put at the front of the chain.
     **/
    ["java:type:java.util.ArrayList<com.imageworks.common.SpiIce.SpiIceCause>:java.util.ArrayList<com.imageworks.common.SpiIce.SpiIceCause>"]
    sequence<SpiIceCause> SpiIceCauseSeq;

    /**
     * The base class of all exceptions thrown by an Ice application.
     * Subclasses of SpiIceException provide specific meaning, but not
     * necessarily add any additional fields.
     **/
    exception SpiIceException
    {
        string message;
        StringSeq stackTrace;
        SpiIceCauseSeq causedBy;
    };

    /**
     * This exception is thrown when an illegal argument was used.
     **/
    exception SpiIceIllegalArgumentException
        extends SpiIceException
    {
    };

    /**
     * This exception is thrown when an object does not exist on the
     * server.
     **/
    exception SpiIceDoesNotExistException
        extends SpiIceException
    {
    };

    /**
     * This exception is thrown for all other runtime errors.
     **/
    exception SpiIceRuntimeException
        extends ::SpiIce::SpiIceException
    {
    };

};

#endif

/*
 * Local Variables:
 * mode: c++
 * End:
 */
