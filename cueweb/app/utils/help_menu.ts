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
 * Help menu entries - CueGUI parity (the "Help" menu in
 * `cuegui/cuegui/MainWindow.py`). Each entry opens an external URL in a
 * new tab. URLs are configurable at build time via NEXT_PUBLIC_* env vars
 * so deployments can point Suggestions / Bug reports at internal trackers.
 */

export interface HelpItem {
  label: string;
  href: string;
}

// Defaults mirror CueGUI exactly (cuegui/cuegui/config/cuegui.yaml lines
// `links.user_guide`, `links.issue.create + links.issue.suggestion`,
// `links.issue.create + links.issue.bug`).
const GH_NEW_ISSUE =
  "https://github.com/AcademySoftwareFoundation/OpenCue/issues/new";

const DEFAULTS = {
  docs: "https://www.opencue.io/docs/",
  suggestions: `${GH_NEW_ISSUE}?labels=enhancement&template=enhancement.md`,
  bugs: `${GH_NEW_ISSUE}?labels=bug&template=bug_report.md`,
};

function pick(envValue: string | undefined, fallback: string): string {
  const trimmed = (envValue ?? "").trim();
  return trimmed.length > 0 ? trimmed : fallback;
}

export const HELP_ITEMS: HelpItem[] = [
  {
    label: "Online User Guide",
    href: pick(process.env.NEXT_PUBLIC_DOCS_URL, DEFAULTS.docs),
  },
  {
    label: "Make a Suggestion",
    href: pick(process.env.NEXT_PUBLIC_SUGGESTIONS_URL, DEFAULTS.suggestions),
  },
  {
    label: "Report a Bug",
    href: pick(process.env.NEXT_PUBLIC_BUGS_URL, DEFAULTS.bugs),
  },
];
