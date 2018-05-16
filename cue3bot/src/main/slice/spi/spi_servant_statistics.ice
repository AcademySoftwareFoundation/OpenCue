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


#ifndef SPI_SERVANT_STATISTICS_ICE
#define SPI_SERVANT_STATISTICS_ICE

/**
 * Design Notes
 * ============
 *
 * Idempotent Methods
 * ------------------
 *
 * Ice allows methods to be marked as idempotent.  This allows the Ice
 * client side to perform more aggressive recovery for network
 * failures.  Methods are only marked as idempotent if multiple
 * successive calls to the same operation have identical effects on
 * the server and return exactly the same result.
 *
 * For example, presume that Foo::remove() is marked as idempotent.
 *
 * 1) Client calls Foo::remove().
 * 2) Network connection to the server is lost but the server does
 *    delete the foo object.
 * 3) The client Ice runtime retries the Foo::remove() call.
 * 4) Server responds with a DoesNotExistException.
 *
 * The return of the exception is not correct.
 *
 * See pages 2 and 3 of http://www.zeroc.com/newsletter/issue7.pdf for
 * another example.
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
#include <spi_exceptions.ice>

[["java:package:com.imageworks.common"]]
[["python:package:spi"]]
module SpiIce
{
    /**
     * The following definitions are for servant performance
     * statistics.
     **/

    /**
     * This structure holds the number of requests and the cumulative
     * service time in nanoseconds for a portion or all of the
     * requests for a single Ice method.
     **/
    struct PartitionedStatistics
    {
        /**
         * The count of requests.
         **/
        long requestCount;

        /**
         * The cumulative service time in nanoseconds.
         **/
        long cumulativeServiceTimeNanos;
    };

    /**
     * This dictionary holds all the available statistics for a single
     * Ice method.  Different sets of statistics are available through
     * different keys into the dictionary, such as the count and
     * cumulative service time for only successful requests, or only
     * failed requests.
     *
     * The following keys exist in the dictionary.  The difference
     * between a successful and a failed request is a successful
     * method did not throw an exception while a failed method threw
     * an exception to the client.
     *
     *   "all"                   all requests on the Ice method
     *   "successful"            only successful responses from the
     *                           Ice method
     *   "failed"                only failed responses from the Ice
     *                           method
     *   "successful_cache_skip" direct invocations that were
     *                           successful
     *   "successful_cache_hit"  cache hits that returned a successful
     *                           response to the client
     *   "successful_cache_miss" cache miss that returned a successful
     *                           response to the client
     *   "failed_cache_skip"     direct invocations that failed
     *   "failed_cache_hit"      cache hits that returned an exception
     *                           to the client
     *   "failed_cache_miss"     cache misses that returned an exception
     *                           to the client
     **/
    ["java:type:java.util.HashMap<java.lang.String,PartitionedStatistics>:java.util.HashMap<java.lang.String,PartitionedStatistics>"]
    dictionary<string,PartitionedStatistics> MethodStatistics;

    /**
     * This structure uniquely identifies an Ice method by the
     * servant's static ID and method name.
     */
    struct MethodId
    {
        /**
         * The static identity of the servant.
         **/
        string servantStaticId;

        /**
         * The method name.
         **/
        string methodName;
    };

    /**
     * This dictionary contains all the statistics for a single
     * servant.
     **/
    ["java:type:java.util.HashMap<java.lang.String,java.util.HashMap<java.lang.String,PartitionedStatistics>>:java.util.HashMap<java.lang.String,java.util.HashMap<java.lang.String,PartitionedStatistics>>"]
    dictionary<string,MethodStatistics> MethodStatisticsByMethodName;

    /**
     * This dictionary contains all the statistics for all servants.
     * It is keyed by the method ID.
     **/
    ["java:type:java.util.HashMap<MethodId,java.util.HashMap<java.lang.String,PartitionedStatistics>>:java.util.HashMap<MethodId,java.util.HashMap<java.lang.String,PartitionedStatistics>>"]
    dictionary<MethodId,MethodStatistics> MethodStatisticsByMethodId;

    /**
     * A static interface that returns all the information on Ice
     * servants and methods.
     **/
    interface ServantStatisticsStatic
    {
        /**
         * Return a list of all the servant static IDs running in the
         * server.
         *
         * @return an array of all the servant's static IDs.
         * @throws SpiIceException
         **/
        ["cpp:const"]
        idempotent StringSeq
        getAllServantIds()
            throws SpiIceException;

        /**
         * Given an servant static ID, return the statistics on all
         * its methods.
         *
         * @param servantStaticId the servant static ID
         * @return a dictionary keyed by the method name whose values
         *         are the statistics for that methods
         * @throws SpiIceDoesNotExistException if there is no servant
         *         with the static ID; SpiIceException for any other
         *         exceptions
         */
        ["cpp:const"]
        idempotent MethodStatisticsByMethodName
        getServantStatistics(string servantStaticId)
            throws SpiIceException;

        /**
         * Return the method statistics on all servants.
         *
         * @return a dictionary keyed by the method ID whose values
         *         are the statistics for that methods
         * @throws SpiIceException
         */
        ["cpp:const"]
        idempotent MethodStatisticsByMethodId
        getAllServantStatistics()
            throws SpiIceException;
    };

};

#endif

/*
 * Local Variables:
 * mode: c++
 * End:
 */
