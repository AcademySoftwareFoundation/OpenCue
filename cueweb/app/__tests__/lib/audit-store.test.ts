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

import { promises as fs } from "fs";
import os from "os";
import path from "path";

// STORE_PATH is captured at module load from CUEWEB_AUDIT_STORE, so set a
// unique temp path BEFORE requiring the module under test.
const TMP_STORE = path.join(
  os.tmpdir(),
  `cueweb-audit-test-${process.pid}-${Date.now()}.jsonl`,
);
process.env.CUEWEB_AUDIT_STORE = TMP_STORE;

const {
  recordAudit,
  readAudit,
  readAuditFacets,
  auditStorePath,
} = require("@/lib/audit-store") as typeof import("@/lib/audit-store");

afterAll(async () => {
  await fs.rm(TMP_STORE, { force: true }).catch(() => undefined);
});

// Reset the file between tests so each starts from a clean trail.
beforeEach(async () => {
  await fs.rm(TMP_STORE, { force: true }).catch(() => undefined);
});

function rec(over: Partial<Parameters<typeof recordAudit>[0]> = {}) {
  return {
    at: new Date().toISOString(),
    actor: "alice@example.com",
    category: "job" as const,
    action: "Kill",
    target: "job:comp_v1",
    facility: "DEV",
    result: "success" as const,
    ...over,
  };
}

describe("audit-store", () => {
  it("reports the configured store path", () => {
    expect(auditStorePath()).toBe(TMP_STORE);
  });

  it("returns an empty page when nothing has been recorded", async () => {
    const page = await readAudit();
    expect(page).toEqual({ records: [], total: 0 });
  });

  it("records and reads back events, newest first", async () => {
    await recordAudit(rec({ at: "2026-06-22T10:00:00.000Z", action: "Pause" }));
    await recordAudit(rec({ at: "2026-06-22T11:00:00.000Z", action: "Kill" }));

    const { records, total } = await readAudit();
    expect(total).toBe(2);
    expect(records.map((r) => r.action)).toEqual(["Kill", "Pause"]);
  });

  it("filters by actor (case-insensitive substring), category and result", async () => {
    await recordAudit(rec({ actor: "alice@example.com", category: "job" }));
    await recordAudit(rec({ actor: "bob@example.com", category: "host", action: "Lock Host" }));
    await recordAudit(rec({ actor: "alice@example.com", result: "error", error: "boom" }));

    expect((await readAudit({ actor: "ALICE" })).total).toBe(2);
    expect((await readAudit({ category: "host" })).total).toBe(1);
    expect((await readAudit({ result: "error" })).total).toBe(1);
  });

  it("filters by time window", async () => {
    await recordAudit(rec({ at: "2026-06-20T00:00:00.000Z" }));
    await recordAudit(rec({ at: "2026-06-22T00:00:00.000Z" }));
    await recordAudit(rec({ at: "2026-06-24T00:00:00.000Z" }));

    const page = await readAudit({
      since: "2026-06-21T00:00:00.000Z",
      until: "2026-06-23T00:00:00.000Z",
    });
    expect(page.total).toBe(1);
    expect(page.records[0].at).toBe("2026-06-22T00:00:00.000Z");
  });

  it("searches across actor / action / target / error", async () => {
    await recordAudit(rec({ action: "Kill", target: "job:render_final" }));
    await recordAudit(rec({ action: "Pause", target: "job:other", result: "error", error: "timeout" }));

    expect((await readAudit({ search: "render_final" })).total).toBe(1);
    expect((await readAudit({ search: "timeout" })).total).toBe(1);
    expect((await readAudit({ search: "nope" })).total).toBe(0);
  });

  it("paginates with limit and offset while reporting the full total", async () => {
    for (let i = 0; i < 5; i++) {
      await recordAudit(rec({ at: `2026-06-22T0${i}:00:00.000Z`, action: `A${i}` }));
    }
    const page = await readAudit({ limit: 2, offset: 1 });
    expect(page.total).toBe(5);
    expect(page.records).toHaveLength(2);
    // Newest first => A4, A3, A2, A1, A0; offset 1 + limit 2 => A3, A2.
    expect(page.records.map((r) => r.action)).toEqual(["A3", "A2"]);
  });

  it("exposes distinct actors and categories as facets", async () => {
    await recordAudit(rec({ actor: "alice@example.com", category: "job" }));
    await recordAudit(rec({ actor: "bob@example.com", category: "host" }));
    await recordAudit(rec({ actor: "alice@example.com", category: "job" }));

    const facets = await readAuditFacets();
    expect(facets.actors).toEqual(["alice@example.com", "bob@example.com"]);
    expect(facets.categories).toEqual(["host", "job"]);
  });
});
