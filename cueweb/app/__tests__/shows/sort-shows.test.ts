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

import { sortShows } from "@/app/shows/sort-shows";
import { Show } from "@/app/utils/get_utils";

const show = (name: string, active: boolean): Show => ({ id: name, name, active });

describe("sortShows", () => {
  it("places active shows before inactive ones", () => {
    const result = sortShows([show("a", false), show("b", true)]);
    expect(result.map(s => s.name)).toEqual(["b", "a"]);
  });

  it("sorts alphabetically (case-insensitive) within the same active state", () => {
    const result = sortShows([
      show("Zulu", true),
      show("alpha", true),
      show("Mike", true),
    ]);
    expect(result.map(s => s.name)).toEqual(["alpha", "Mike", "Zulu"]);
  });

  it("orders active block before inactive block, each alphabetised", () => {
    const result = sortShows([
      show("inactiveB", false),
      show("activeB", true),
      show("inactiveA", false),
      show("activeA", true),
    ]);
    expect(result.map(s => s.name)).toEqual([
      "activeA",
      "activeB",
      "inactiveA",
      "inactiveB",
    ]);
  });

  it("does not mutate the input array", () => {
    const input = [show("b", true), show("a", true)];
    const copy = [...input];
    sortShows(input);
    expect(input).toEqual(copy);
  });

  it("handles an empty list", () => {
    expect(sortShows([])).toEqual([]);
  });
});
