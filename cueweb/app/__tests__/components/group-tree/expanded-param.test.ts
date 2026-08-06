/*
 * Copyright Contributors to the OpenCue Project
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

import {
    parseExpandedParam,
    serializeExpandedParam,
} from "@/components/group-tree/expanded-param";

describe("parseExpandedParam", () => {
    it("returns an empty set for null", () => {
        expect(parseExpandedParam(null)).toEqual(new Set());
    });

    it("returns an empty set for an empty string", () => {
        expect(parseExpandedParam("")).toEqual(new Set());
    });

    it("splits a comma-separated list of ids", () => {
        expect(parseExpandedParam("a,b,c")).toEqual(new Set(["a", "b", "c"]));
    });

    it("drops empty entries from consecutive or trailing commas", () => {
        expect(parseExpandedParam("a,,b,")).toEqual(new Set(["a", "b"]));
    });

    it("dedupes repeated ids", () => {
        expect(parseExpandedParam("a,b,a,a")).toEqual(new Set(["a", "b"]));
    });
});

describe("serializeExpandedParam", () => {
    it("returns an empty string for an empty set", () => {
        expect(serializeExpandedParam(new Set())).toEqual("");
    });

    it("joins ids with commas", () => {
        expect(serializeExpandedParam(new Set(["a", "b", "c"]))).toEqual("a,b,c");
    });

    it("round-trips with parseExpandedParam (insertion order preserved)", () => {
        const set = new Set(["x", "y", "z"]);
        expect(parseExpandedParam(serializeExpandedParam(set))).toEqual(set);
    });
});
