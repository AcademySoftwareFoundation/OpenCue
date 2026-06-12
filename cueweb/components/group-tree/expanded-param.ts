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

// Parse the comma-separated list of group ids in the `expanded` search param.
export function parseExpandedParam(value: string | null): Set<string> {
  if (!value) return new Set();
  return new Set(value.split(",").filter(part => part.length > 0));
}

// Serialize the set back to a comma-separated string. Empty set returns "".
export function serializeExpandedParam(ids: Set<string>): string {
  return Array.from(ids).join(",");
}
