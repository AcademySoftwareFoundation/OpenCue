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

// Node-runtime-only side of the instrumentation hook. instrumentation.ts
// guards on NEXT_RUNTIME === "nodejs" before importing this file, so
// the edge bundle never sees the native modules transitively pulled in
// by `ensureBootstrapAdmin`.

import { ensureBootstrapAdmin } from "./lib/rbac/bootstrap";

const authProviders = (process.env.NEXT_PUBLIC_AUTH_PROVIDER || "")
  .split(",")
  .map((s) => s.trim().toLowerCase())
  .filter(Boolean);

if (authProviders.includes("local")) {
  ensureBootstrapAdmin().catch((err) => {
    // eslint-disable-next-line no-console
    console.error(
      "CueWeb: bootstrap admin init failed at startup:",
      err instanceof Error ? err.message : String(err),
    );
  });
}
