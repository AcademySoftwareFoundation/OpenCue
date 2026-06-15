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

// Helpers shared by the frame preview side panel and the image-serving
// API route. No Node/browser-only APIs here so both can import it.

// Formats a browser <img> can render directly. SVG is intentionally excluded:
// see NON_WEB_IMAGE_EXTENSIONS.
export const WEB_IMAGE_EXTENSIONS = new Set([
  "png", "jpg", "jpeg", "gif", "webp", "bmp", "avif",
]);

// Formats the preview route won't serve inline (surface a "preview not
// supported" message and let the user open them externally). Mostly render
// formats browsers can't display, plus SVG - which a browser *can* render but
// is blocked here because serving it same-origin would allow script execution.
export const NON_WEB_IMAGE_EXTENSIONS = new Set([
  "exr", "tif", "tiff", "dpx", "tx", "sxr", "hdr", "cin", "rat", "svg",
]);

export function fileExtension(p: string): string {
  const base = p.split(/[?#]/)[0];
  const dot = base.lastIndexOf(".");
  return dot >= 0 ? base.slice(dot + 1).toLowerCase() : "";
}

export function isWebRenderableImage(p: string): boolean {
  return WEB_IMAGE_EXTENSIONS.has(fileExtension(p));
}

export function isNonWebImage(p: string): boolean {
  return NON_WEB_IMAGE_EXTENSIONS.has(fileExtension(p));
}

function pad(n: number, width: number): string {
  const s = String(n);
  return s.length >= width ? s : "0".repeat(width - s.length) + s;
}

// Substitute a frame number into the common frame-number tokens found in
// OpenCue / outline output-path specs, producing a concrete per-frame path.
//   ####        -> zero-padded to the run length        (e.g. 0042)
//   @@@@        -> Houdini-style, same as #
//   %04d / %d   -> printf style
//   $F, $F4     -> Houdini variables ($F4 = pad to 4)
// Paths with no token are returned unchanged (may be a single file or dir).
export function substituteFrameNumber(outputPath: string, frameNumber: number): string {
  let out = outputPath;
  out = out.replace(/#+/g, (m) => pad(frameNumber, m.length));
  out = out.replace(/@+/g, (m) => pad(frameNumber, m.length));
  out = out.replace(/%0(\d+)d/g, (_m, w) => pad(frameNumber, Number.parseInt(w, 10)));
  out = out.replace(/%d/g, () => String(frameNumber));
  out = out.replace(/\$F(\d+)/g, (_m, w) => pad(frameNumber, Number.parseInt(w, 10)));
  out = out.replace(/\$F\b/g, () => String(frameNumber));
  return out;
}

// Build the ordered list of candidate image files to try for a frame, given
// the layer's registered output paths. De-duplicated, original order kept.
export function resolveFramePreviewCandidates(
  outputPaths: string[],
  frameNumber: number,
): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const p of outputPaths) {
    if (!p) continue;
    const resolved = substituteFrameNumber(p, frameNumber);
    if (!seen.has(resolved)) {
      seen.add(resolved);
      out.push(resolved);
    }
  }
  return out;
}
