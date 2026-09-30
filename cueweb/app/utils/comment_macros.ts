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

// Predefined comment macros — mirrors CueGUI's QSettings-based macro list in
// cuegui/cuegui/Comments.py. Stored per-browser in localStorage.

const STORAGE_KEY = "cueweb-comment-macros";

export type CommentMacro = {
  name: string;
  subject: string;
  message: string;
};

export function loadCommentMacros(): CommentMacro[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (m): m is CommentMacro =>
        m && typeof m.name === "string" && typeof m.subject === "string" && typeof m.message === "string"
    );
  } catch {
    return [];
  }
}

function saveAll(macros: CommentMacro[]): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(macros));
}

// Upsert by name. If a macro with `replaceName` exists it is replaced/renamed.
export function upsertCommentMacro(macro: CommentMacro, replaceName?: string): CommentMacro[] {
  const macros = loadCommentMacros();
  const filtered = macros.filter((m) => m.name !== macro.name && m.name !== replaceName);
  const next = [...filtered, macro].sort((a, b) => a.name.localeCompare(b.name));
  saveAll(next);
  return next;
}

export function deleteCommentMacro(name: string): CommentMacro[] {
  const next = loadCommentMacros().filter((m) => m.name !== name);
  saveAll(next);
  return next;
}
