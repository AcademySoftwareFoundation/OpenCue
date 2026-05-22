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

/**
 * Next.js instrumentation hook
 * (https://nextjs.org/docs/app/api-reference/file-conventions/instrumentation).
 *
 * Runs once per server process on startup. The edge runtime cannot
 * load the native modules (`better-sqlite3`, `argon2`) the bootstrap
 * flow needs, so we delegate to a node-only file via a runtime guard.
 * Splitting it this way lets webpack tree-shake the node code out of
 * the edge build entirely.
 */
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./instrumentation.node");
  }
}
