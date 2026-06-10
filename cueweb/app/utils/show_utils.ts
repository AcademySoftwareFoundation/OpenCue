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

import { accessGetApi } from "./api_utils";
import type { Show } from "./get_utils";

// Single source of truth: Show and getShows live in get_utils with the other
// object getters; re-exported here so the Shows feature imports from one place.
export type { Show };
export { getShows } from "./get_utils";

// Show names must be alphanumeric only (no spaces, dashes, or punctuation).
export function isValidShowName(name: string): boolean {
  return /^[a-zA-Z0-9]+$/.test(name);
}

// Returns the show with the given name, or null if not found.
export async function findShow(name: string): Promise<Show | null> {
  const body = JSON.stringify({ name });
  const response = await accessGetApi("/api/show/findshow", body);
  if (!response || response.notFound) return null;
  return response.show ?? null;
}

// Creates a new show with the given name and returns it. Throws on failure so
// the modal form can surface the reason inline.
export async function createShow(name: string): Promise<Show> {
  const body = JSON.stringify({ name });
  const response = await accessGetApi("/api/show/createshow", body);
  if (!response || !response.show) {
    throw new Error("Failed to create show");
  }
  return response.show;
}
