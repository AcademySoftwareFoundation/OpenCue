"use client";

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

import type { Frame } from "@/app/frames/frame-columns";
import type { Job } from "@/app/jobs/columns";
import { fetchLayerOutputPaths } from "@/app/utils/action_utils";
import { getLayersForJob } from "@/app/utils/get_utils";
import { handleError } from "@/app/utils/notify_utils";
import {
  isNonWebImage,
  isWebRenderableImage,
  resolveFramePreviewCandidates,
} from "@/app/utils/preview_utils";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";

// "Frame preview thumbnail viewer". A right-side slide-over that loads a
// rendered frame image. Opened via the `cueweb:open-frame-thumbnail` event the
// frame row's Preview button dispatches. PNG/JPG/etc render inline (lazy);
// EXR-like formats and missing outputs surface a clear message.

type Status = "resolving" | "loading" | "ok" | "error" | "unsupported" | "nopath";

const previewSrc = (p: string) => `/api/frame/preview?path=${encodeURIComponent(p)}`;

export function FramePreviewPanel({ job }: { job?: Job }) {
  const [open, setOpen] = React.useState(false);
  const [frame, setFrame] = React.useState<Frame | null>(null);
  const [status, setStatus] = React.useState<Status>("resolving");
  // All resolved per-frame candidate paths (for display) and the subset the
  // browser can render, plus a pointer used to fall through on load error.
  const [candidates, setCandidates] = React.useState<string[]>([]);
  const [webCandidates, setWebCandidates] = React.useState<string[]>([]);
  const [webIdx, setWebIdx] = React.useState(0);

  const resolve = React.useCallback(
    async (f: Frame) => {
      setStatus("resolving");
      setCandidates([]);
      setWebCandidates([]);
      setWebIdx(0);
      if (!job) {
        setStatus("nopath");
        return;
      }
      try {
        const layers = await getLayersForJob(job);
        const layer = layers.find((l) => l.name === f.layerName);
        const paths = layer ? await fetchLayerOutputPaths(layer) : [];
        const resolved = resolveFramePreviewCandidates(paths, f.number);
        setCandidates(resolved);
        const web = resolved.filter(isWebRenderableImage);
        setWebCandidates(web);
        if (web.length > 0) {
          setStatus("loading");
        } else if (resolved.some(isNonWebImage)) {
          setStatus("unsupported");
        } else {
          setStatus("nopath");
        }
      } catch (error) {
        handleError(error, "Could not resolve frame preview");
        setStatus("error");
      }
    },
    [job],
  );

  React.useEffect(() => {
    function handler(e: Event) {
      const f = (e as CustomEvent<{ frame?: Frame }>).detail?.frame;
      if (!f) return;
      setFrame(f);
      setOpen(true);
      resolve(f);
    }
    window.addEventListener("cueweb:open-frame-thumbnail", handler);
    return () => window.removeEventListener("cueweb:open-frame-thumbnail", handler);
  }, [resolve]);

  const currentPath = webCandidates[webIdx];

  function onImgError() {
    // Try the next renderable candidate; give up (error) once exhausted.
    if (webIdx + 1 < webCandidates.length) {
      setWebIdx((i) => i + 1);
      setStatus("loading");
    } else {
      setStatus("error");
    }
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetContent side="right" className="w-full sm:max-w-xl">
        <SheetTitle>Frame Preview</SheetTitle>
        <SheetDescription className="break-all font-mono text-xs">{frame?.name}</SheetDescription>

        <div className="mt-4 flex min-h-[200px] items-center justify-center rounded-md border border-border bg-muted/30 p-2">
          {status === "resolving" && (
            <p className="text-sm text-muted-foreground">Resolving output path...</p>
          )}

          {(status === "loading" || status === "ok") && currentPath && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={currentPath}
              src={previewSrc(currentPath)}
              alt={`Preview of ${frame?.name ?? "frame"}`}
              loading="lazy"
              onLoad={() => setStatus("ok")}
              onError={onImgError}
              className="max-h-[70vh] max-w-full object-contain"
            />
          )}

          {status === "unsupported" && (
            <p className="px-4 text-center text-sm text-muted-foreground">
              Preview not supported in browser for this format
              {candidates[0] ? ` (.${candidates[0].split(".").pop()})` : ""}. Use the frame menu&apos;s
              &ldquo;Preview All&rdquo; to open it in an external image viewer.
            </p>
          )}

          {status === "error" && (
            <p className="px-4 text-center text-sm text-muted-foreground">
              Could not load the rendered image. The file may not exist yet, or it isn&apos;t
              readable by CueWeb (the render output must be mounted into the container).
            </p>
          )}

          {status === "nopath" && (
            <p className="px-4 text-center text-sm text-muted-foreground">
              {job
                ? "No output path is registered for this frame's layer yet."
                : "Frame preview needs the parent job context, which isn't available here."}
            </p>
          )}
        </div>

        {status === "ok" && currentPath ? (
          <p className="mt-2 break-all font-mono text-[11px] text-muted-foreground">{currentPath}</p>
        ) : null}

        {candidates.length > 0 ? (
          <div className="mt-4">
            <span className="text-xs font-medium text-muted-foreground">Candidate output paths</span>
            <ul className="mt-1 max-h-40 space-y-1 overflow-auto rounded-md border border-input p-2 text-[11px]">
              {candidates.map((p, i) => (
                <li key={i} className="break-all font-mono">{p}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
