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

#ifndef SPI_SEARCH_CRITERIA_ICE
#define SPI_SEARCH_CRITERIA_ICE

/**
 * The classes in this Slice file provide a way for Ice clients to
 * search for data with different criteria.
 **/
[["java:package:com.imageworks.common"]]
[["python:package:spi"]]
module SpiIce
{
    /**
     * Base class for a criterion for matching floating point values.
     **/
    class FloatSearchCriterion
    {
    };

    /**
     * Instances of this class indicate that floating point values
     * must have the same value in this class.
     **/
    class EqualsFloatSearchCriterion
        extends FloatSearchCriterion
    {
        /**
         * Matching floating point values will equal this value.
         **/
        float value;
    };

    /**
     * Instances of this class indicate that floating point values
     * must be less than the value in this class.
     **/
    class LessThanFloatSearchCriterion
        extends FloatSearchCriterion
    {
        /**
         * Matching floating point values will be less than this
         * value.
         **/
        float value;
    };

    /**
     * Instances of this class indicate that floating point values
     * must be greater than the value in this class.
     **/
    class GreaterThanFloatSearchCriterion
        extends FloatSearchCriterion
    {
        /**
         * Matching floating point values will be greater than this
         * value.
         **/
        float value;
    };

    /**
     * Instances of this class indicate that floating point values
     * must be within the range of values in this class.
     **/
    class InRangeFloatSearchCriterion
        extends FloatSearchCriterion
    {
        /**
         * Matching floating point values will be greater than this
         * value.
         **/
        float min;

        /**
         * Matching floating point values will be less than this
         * value.
         */
        float max;
    };

    /**
     * Base class for a criterion for matching integer values.
     **/
    class IntegerSearchCriterion
    {
    };

    /**
     * Instances of this class indicate that integer values must have
     * the same value in this class.
     **/
    class EqualsIntegerSearchCriterion
        extends IntegerSearchCriterion
    {
        /**
         * Matching integer values will equal this value.
         **/
        int value;
    };

    /**
     * Instances of this class indicate that integer values must be
     * less than the value in this class.
     **/
    class LessThanIntegerSearchCriterion
        extends IntegerSearchCriterion
    {
        /**
         * Matching integer values will be less than this value.
         **/
        int value;
    };

    /**
     * Instances of this class indicate that integer values must be
     * greater than the value in this class.
     **/
    class GreaterThanIntegerSearchCriterion
        extends IntegerSearchCriterion
    {
        /**
         * Matching integer values will be greater than this value.
         **/
        int value;
    };

    /**
     * Instances of this class indicate that integer values must be
     * within the range of values in this class.
     **/
    class InRangeIntegerSearchCriterion
        extends IntegerSearchCriterion
    {
        /**
         * Matching integer values will be greater than this value.
         **/
        int min;

        /**
         * Matching integer values will be less than this value.
         */
        int max;
    };

    /**
     * Base class for a criterion to match strings.
     **/
    class StringSearchCriterion
    {
    };

   /**
     * Instances of this class indicate that strings must exactly
     * match the string in this class.
     **/
    class EqualsStringSearchCriterion
        extends StringSearchCriterion
    {
        /**
         * Matching strings will have the exact same contents as this
         * string.
         **/
        string value;
    };

    /**
     * Instances of this class indicate that strings must match the
     * beginning of this string.
     **/
    class StartsWithStringSearchCriterion
        extends StringSearchCriterion
    {
        /**
         * Matching strings will begin with the same contents as this
         * string.
         **/
        string prefix;
    };

    /**
     * Instances of this class indicate that strings must match the
     * end of this string.
     **/
    class EndsWithStringSearchCriterion
        extends StringSearchCriterion
    {
        /**
         * Matching strings will end with the same contents as this
         * string.
         **/
        string suffix;
    };

    /**
     * Instances of this class indicate that strings must match the
     * regular expression in this string.
     **/
    class RegexStringSearchCriterion
        extends StringSearchCriterion
    {
        /**
         * Matching strings will match this regex.
         **/
        string regex;
    };

    /**
     * An optional criterion for floating point values.
     **/
    sequence <FloatSearchCriterion> FloatSearchCriterionOpt;

    /**
     * An optional criterion for integer values.
     **/
    sequence <IntegerSearchCriterion> IntegerSearchCriterionOpt;

    /**
     * An optional criterion for strings.
     **/
    sequence <StringSearchCriterion> StringSearchCriterionOpt;

    /**
     * A sequence of criteria for searching for floating point values.
     **/
    sequence <FloatSearchCriterion> FloatSearchCriterionSeq;

    /**
     * A sequence of criteria for searching for integer values.
     **/
    sequence <IntegerSearchCriterion> IntegerSearchCriterionSeq;

    /**
     * A sequence of criteria for searching for strings.
     **/
    sequence <StringSearchCriterion> StringSearchCriterionSeq;
};
#endif

/*
 * Local Variables:
 * mode: c++
 * End:
 */
