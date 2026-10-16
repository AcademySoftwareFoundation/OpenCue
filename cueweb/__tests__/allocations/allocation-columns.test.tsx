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

import { allocationColumns } from "@/app/allocations/allocation-columns";
import { AllocationRow } from "@/app/allocations/allocation-utils";

describe("allocationColumns name link", () => {
  it("links to the hosts page using the `alloc` param the hosts page reads", () => {
    const nameColumn = allocationColumns.find(
      (column: any) => column.accessorKey === "name",
    );
    expect(nameColumn).toBeDefined();
    expect(nameColumn!.cell).toBeDefined();

    const row = { original: { name: "local.general" } as AllocationRow };
    const cellRenderer = nameColumn!.cell as (context: any) => any;
    const element = cellRenderer({ row });

    // Regression check for https://github.com/AcademySoftwareFoundation/OpenCue/issues/2536:
    // the link used to use `?allocation=`, but the hosts page's filter
    // (parseSetParam in app/hosts/page.tsx) only reads `?alloc=`, so the
    // click-through never actually filtered the table.
    expect(element.props.href).toBe("/hosts?alloc=local.general");
  });

  it("URL-encodes allocation names with special characters", () => {
    const nameColumn = allocationColumns.find(
      (column: any) => column.accessorKey === "name",
    );
    const row = { original: { name: "a/b c" } as AllocationRow };
    const cellRenderer = nameColumn!.cell as (context: any) => any;
    const element = cellRenderer({ row });

    expect(element.props.href).toBe("/hosts?alloc=a%2Fb%20c");
  });
});
