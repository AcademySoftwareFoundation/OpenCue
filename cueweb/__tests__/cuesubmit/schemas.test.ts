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

import { zodResolver } from "@hookform/resolvers/zod";
import type { ResolverOptions } from "react-hook-form";

import { submissionSchema, type Submission, type SubmissionInput } from "@/app/cuesubmit/lib/schemas";

// Runs the schema through the same resolver the CueSubmit form uses, so a
// zod / @hookform/resolvers version mismatch shows up here rather than as a
// form that throws on submit.
const resolve = (values: SubmissionInput) =>
  zodResolver(submissionSchema)(values, undefined, {
    fields: {},
    shouldUseNativeValidation: false,
  } as ResolverOptions<SubmissionInput>);

describe("submissionSchema via zodResolver", () => {
  it("returns field errors instead of throwing for invalid input", async () => {
    const result = await resolve({
      job: { name: "", show: "", shot: "sh010", user: "artist" },
      layers: [{ name: "render", frameSpec: "1-10", jobType: "Shell", chunkSize: "0" }],
    });

    expect(result.values).toEqual({});
    expect(result.errors).toMatchObject({
      job: {
        name: { message: "Job Name is required." },
        show: { message: "Show is required." },
      },
      layers: [{ chunkSize: { type: "too_small" } }],
    });
  });

  it("applies defaults and coerces numeric fields for valid input", async () => {
    const result = await resolve({
      job: { name: "job", show: "show", shot: "sh010", user: "artist" },
      layers: [{ name: "render", frameSpec: "1-10", jobType: "Shell", chunkSize: "4" }],
    });

    expect(result.errors).toEqual({});
    const { job, layers } = result.values as Submission;
    expect(job.facility).toBe("");
    expect(layers[0]).toMatchObject({
      chunkSize: 4,
      memory: "256m",
      services: [],
      shell: { command: "" },
    });
  });
});
