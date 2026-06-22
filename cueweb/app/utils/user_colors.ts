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

import * as React from "react";

// CueGUI's 15 predefined "Set user color" swatches. These mirror
// cuegui/config/cuegui.yaml -> style.colors.background (RGB 0-255). Like
// CueGUI, the whole job row is painted with the chosen color; the palette is
// intentionally dark so light text reads well on top of it.
export interface UserColorPreset {
  name: string;
  hex: string;
}

export const CUEGUI_USER_COLORS: UserColorPreset[] = [
  { name: "Dark Blue", hex: "#323264" }, //    [50, 50, 100]
  { name: "Dark Yellow", hex: "#646432" }, //  [100, 100, 50]
  { name: "Dark Green", hex: "#003200" }, //   [0, 50, 0]
  { name: "Dark Brown", hex: "#321e00" }, //   [50, 30, 0]
  { name: "Purple", hex: "#500050" }, //       [80, 0, 80]
  { name: "Teal", hex: "#005050" }, //         [0, 80, 80]
  { name: "Orange", hex: "#643200" }, //       [100, 50, 0]
  { name: "Maroon", hex: "#460023" }, //       [70, 0, 35]
  { name: "Forest Green", hex: "#003c1e" }, // [0, 60, 30]
  { name: "Lavender", hex: "#5a3c5a" }, //     [90, 60, 90]
  { name: "Crimson", hex: "#640032" }, //      [100, 0, 50]
  { name: "Navy", hex: "#003264" }, //         [0, 50, 100]
  { name: "Olive", hex: "#505000" }, //        [80, 80, 0]
  { name: "Plum", hex: "#3c143c" }, //         [60, 20, 60]
  { name: "Slate", hex: "#1e4646" }, //        [30, 70, 70]
];

// CueWeb's original bright palette, kept alongside the CueGUI defaults so the
// previously-available swatches stay accessible.
export const CUEWEB_BRIGHT_COLORS: UserColorPreset[] = [
  { name: "Red", hex: "#e03434" },
  { name: "Orange", hex: "#e08a34" },
  { name: "Yellow", hex: "#e0d234" },
  { name: "Green", hex: "#46c246" },
  { name: "Blue", hex: "#3aa3d1" },
  { name: "Violet", hex: "#7c4dd1" },
  { name: "Pink", hex: "#d14da3" },
  { name: "Cyan", hex: "#2ec4d4" },
  { name: "Lime", hex: "#a3d134" },
  { name: "Magenta", hex: "#e034c4" },
];

export const USER_COLORS_KEY = "cueweb.userColors";
export const USER_COLORS_EVENT = "cueweb:user-colors";

export function readUserColors(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(USER_COLORS_KEY);
    if (!raw) return {};
    // Validate the stored shape: tampered/legacy data could be null, an array,
    // or hold non-string values, which would break callers expecting a plain
    // Record<string, string>. Keep only string-valued entries.
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return Object.fromEntries(
      Object.entries(parsed as Record<string, unknown>).filter(
        ([, value]) => typeof value === "string",
      ),
    ) as Record<string, string>;
  } catch {
    return {};
  }
}

export function writeUserColors(map: Record<string, string>): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(USER_COLORS_KEY, JSON.stringify(map));
    // Notify same-tab listeners; the browser's `storage` event only fires
    // on OTHER tabs by default.
    window.dispatchEvent(new CustomEvent(USER_COLORS_EVENT));
  } catch {
    // Quota / private mode; silently ignore.
  }
}

// React hook returning the live jobId -> hex map, refreshing on same-tab
// (custom event) and cross-tab (storage event) updates.
export function useUserColors(): Record<string, string> {
  const [colors, setColors] = React.useState<Record<string, string>>({});
  React.useEffect(() => {
    const refresh = () => setColors(readUserColors());
    refresh();
    window.addEventListener("storage", refresh);
    window.addEventListener(USER_COLORS_EVENT, refresh);
    return () => {
      window.removeEventListener("storage", refresh);
      window.removeEventListener(USER_COLORS_EVENT, refresh);
    };
  }, []);
  return colors;
}

// Pick black or white text for legibility on a given background, using the
// WCAG relative-luminance threshold. CueGUI's palette is dark, so this almost
// always returns white, but it keeps custom (light) colors readable too.
export function readableTextColor(hex: string): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return "inherit";
  const int = parseInt(m[1], 16);
  const r = (int >> 16) & 0xff;
  const g = (int >> 8) & 0xff;
  const b = int & 0xff;
  const srgb = [r, g, b].map((c) => {
    const v = c / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  const luminance = 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
  // Pick the foreground with the higher WCAG contrast ratio against this
  // background, rather than a fixed luminance cutoff that misjudges mid-tones.
  const contrastWithBlack = (luminance + 0.05) / 0.05;
  const contrastWithWhite = 1.05 / (luminance + 0.05);
  return contrastWithBlack >= contrastWithWhite ? "#000000" : "#ffffff";
}
