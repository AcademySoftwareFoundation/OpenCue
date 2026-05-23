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

// Tiny wrapper around the existing /api/show/getshows endpoint so the
// CueSubmit page can populate its Show dropdown without inlining a
// fetch + error-handling block.

export type ShowOption = { id: string; name: string };

export async function fetchShows(): Promise<ShowOption[]> {
  const base = process.env.NEXT_PUBLIC_URL ?? "";
  const res = await fetch(`${base}/api/show/getshows`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
    cache: "no-store",
  });
  if (!res.ok) return [];
  const body = await res.json().catch(() => ({}));
  const shows = (body?.data ?? []) as Array<{
    id?: string;
    name?: string;
    show_id?: string;
    show_name?: string;
  }>;
  return shows
    .map((s) => ({
      id: String(s.id ?? s.show_id ?? s.name ?? ""),
      name: String(s.name ?? s.show_name ?? s.id ?? ""),
    }))
    .filter((s) => s.name);
}
