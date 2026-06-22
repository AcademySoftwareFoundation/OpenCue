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

import type { PluginModule } from "@/lib/plugins";

/**
 * Manifest for the Cue Progress Bar plugin — a CueWeb port of the CueGUI
 * `cueprogbar` sample (cuegui/cuegui/cueguiplugin/cueprogbar/). `load` is a
 * deferred `import()` so the component lands in its own chunk, fetched only
 * when `/plugins/cue-progress-bar` is visited.
 */
export const cueProgressBarPlugin: PluginModule = {
  manifest: {
    name: "cue-progress-bar",
    title: "Cue Progress Bar",
    version: "1.0.0",
    route: "/plugins/cue-progress-bar",
    description: "Live, color-coded frame-state progress bar for a job (CueGUI cueprogbar parity).",
    defaultEnabled: true,
  },
  load: () => import("./cue-progress-bar"),
};
