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
import {
  dropFramesDepends,
  eatAndMarkdoneFrames,
  fetchFrameDepends,
  fetchLayerOutputPaths,
  markdoneFrames,
  markFramesAsWaiting,
  reorderLayerFrames
} from "@/app/utils/action_utils";
import { getFramesForJob, getLayersForJob } from "@/app/utils/get_utils";
import { convertMemoryToString, secondsToHHMMSS } from "@/app/utils/layers_frames_utils";
import { handleError, toastSuccess, toastWarning } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { Status } from "@/components/ui/status";
import { OPEN_DEPENDENCY_WIZARD_EVENT } from "@/components/ui/dependency-wizard-dialog";

const SELECT_CLASS =
  "h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

// "Preview All" hands the layer's rendered output to an external image viewer
// (a browser can't display the frames itself). Both are configurable so each
// site can wire its own viewer:
//   NEXT_PUBLIC_PREVIEW_COMMAND - the command shown + copied (default OpenRV).
//   NEXT_PUBLIC_PREVIEW_URL     - a registered URL scheme the Launch button
//                                 hands off to a local handler (empty = no
//                                 Launch button, copy-the-command only).
// Placeholders {paths} (output paths joined), {job}, {layer}, {frame} are
// substituted in both templates.
const PREVIEW_COMMAND_TEMPLATE = (process.env.NEXT_PUBLIC_PREVIEW_COMMAND ?? "rv {paths}").trim();
const PREVIEW_URL_TEMPLATE = (process.env.NEXT_PUBLIC_PREVIEW_URL ?? "").trim();

function fillTemplate(
  tpl: string,
  ctx: { paths: string[]; job: string; layer: string; frame: string },
  encode: boolean,
): string {
  const enc = (s: string) => (encode ? encodeURIComponent(s) : s);
  return tpl
    .replace(/\{paths\}/g, ctx.paths.map(enc).join(" "))
    .replace(/\{job\}/g, enc(ctx.job))
    .replace(/\{layer\}/g, enc(ctx.layer))
    .replace(/\{frame\}/g, enc(ctx.frame));
}

function frameOf(e: Event): Frame | null {
  return (e as CustomEvent<{ frame?: Frame }>).detail?.frame ?? null;
}

// Reorder a single frame within its layer (CueGUI FrameActions.reorder, which
// reorders per-layer using the selected frames' numbers). We resolve the
// frame's Layer from the parent job, then reorder the single frame number.
function FrameReorderDialog({ job }: { job?: Job }) {
  const [open, setOpen] = React.useState(false);
  const [frame, setFrame] = React.useState<Frame | null>(null);
  const [order, setOrder] = React.useState<"FIRST" | "LAST" | "REVERSE">("FIRST");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const f = frameOf(e);
      if (!f) return;
      setFrame(f);
      setOrder("FIRST");
      setOpen(true);
    }
    window.addEventListener("cueweb:open-frame-reorder", handler);
    return () => window.removeEventListener("cueweb:open-frame-reorder", handler);
  }, []);

  async function apply() {
    if (!frame || !job) return;
    setBusy(true);
    try {
      const layers = await getLayersForJob(job);
      const layer = layers.find((l) => l.name === frame.layerName);
      if (!layer) {
        toastWarning(`Could not find layer "${frame.layerName}" for this frame`);
        return;
      }
      if (await reorderLayerFrames(layer, String(frame.number), order)) setOpen(false);
    } catch (error) {
      handleError(error, "Reorder failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Reorder Frame</DialogTitle>
          <DialogDescription className="break-all font-mono text-xs">{frame?.name}</DialogDescription>
        </DialogHeader>
        <div className="min-w-0 space-y-3 py-2 text-sm">
          <label className="block min-w-0">
            <span className="text-muted-foreground">Order</span>
            <select value={order} onChange={(e) => setOrder(e.target.value as "FIRST" | "LAST" | "REVERSE")} className={SELECT_CLASS} aria-label="Order">
              <option value="FIRST">FIRST</option>
              <option value="LAST">LAST</option>
              <option value="REVERSE">REVERSE</option>
            </select>
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={apply} disabled={busy || !job}>OK</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Confirmation for the destructive per-frame actions (CueGUI questionBoxYesNo).
function FrameConfirmDialog({ job }: { job?: Job }) {
  const [open, setOpen] = React.useState(false);
  const [frame, setFrame] = React.useState<Frame | null>(null);
  const [action, setAction] = React.useState<"dropdepends" | "markaswaiting" | "markdone" | "eatandmarkdone">("markdone");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<{ frame?: Frame; action?: typeof action }>).detail;
      if (!detail?.frame) return;
      setFrame(detail.frame);
      setAction(detail.action ?? "markdone");
      setOpen(true);
    }
    window.addEventListener("cueweb:open-frame-confirm", handler);
    return () => window.removeEventListener("cueweb:open-frame-confirm", handler);
  }, []);

  const COPY: Record<typeof action, { title: string; question: string; destructive: boolean }> = {
    dropdepends: { title: "Drop depends", question: "Drop all dependencies on this frame?", destructive: false },
    markaswaiting: {
      title: "Mark as waiting",
      question: "Mark this frame as waiting? (Ignores its dependencies once.)",
      destructive: false,
    },
    markdone: {
      title: "Mark done",
      question: "Mark this frame done? (Drops any dependencies waiting on it.)",
      destructive: true,
    },
    eatandmarkdone: {
      title: "Eat and Mark done",
      question: "Eat this frame and mark it done? (Drops any dependencies waiting on it.)",
      destructive: true,
    },
  };
  const copy = COPY[action];

  async function confirm() {
    if (!frame) return;
    setBusy(true);
    try {
      let ok = false;
      if (action === "dropdepends") ok = await dropFramesDepends([frame]);
      else if (action === "markaswaiting") ok = await markFramesAsWaiting([frame]);
      else if (action === "markdone") {
        if (!job) { toastWarning("Mark done needs the parent job context"); return; }
        ok = await markdoneFrames(job, [frame]);
      } else {
        if (!job) { toastWarning("Eat and Mark done needs the parent job context"); return; }
        ok = await eatAndMarkdoneFrames(job, [frame]);
      }
      if (ok) setOpen(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{copy.title}</DialogTitle>
          <DialogDescription>{copy.question}</DialogDescription>
        </DialogHeader>
        <p className="break-all font-mono text-xs text-muted-foreground">{frame?.name}</p>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant={copy.destructive ? "destructive" : "default"} onClick={confirm} disabled={busy}>
            {copy.title}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// View Dependencies for a frame (CueGUI DependDialog -> getWhatThisDependsOn).
function FrameDependenciesDialog() {
  const [open, setOpen] = React.useState(false);
  const [frame, setFrame] = React.useState<Frame | null>(null);
  const [depends, setDepends] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(false);

  const load = React.useCallback(async (f: Frame) => {
    setLoading(true);
    try {
      setDepends(await fetchFrameDepends(f));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    function handler(e: Event) {
      const f = frameOf(e);
      if (!f) return;
      setFrame(f);
      setDepends([]);
      setOpen(true);
      load(f);
    }
    window.addEventListener("cueweb:open-frame-dependencies", handler);
    return () => window.removeEventListener("cueweb:open-frame-dependencies", handler);
  }, [load]);

  const onJobOf = (d: any) => d.dependOnJob ?? d.depend_on_job ?? "";
  const onLayerOf = (d: any) => d.dependOnLayer ?? d.depend_on_layer ?? "";
  const onFrameOf = (d: any) => d.dependOnFrame ?? d.depend_on_frame ?? "";

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>
            <span className="break-all font-mono">Dependencies for Frame: {frame?.name ?? ""}</span>
          </DialogTitle>
          <DialogDescription>
            Each row is a depend this frame depends on (getWhatThisDependsOn).
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-[55vh] overflow-auto rounded-md border border-input text-xs">
          <table className="w-full table-auto">
            <thead className="sticky top-0 bg-foreground/[0.04]">
              <tr className="text-left">
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Target</th>
                <th className="px-3 py-2">Active</th>
                <th className="px-3 py-2">OnJob</th>
                <th className="px-3 py-2">OnLayer</th>
                <th className="px-3 py-2">OnFrame</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={6} className="px-3 py-4 text-center text-foreground/60">Loading dependencies...</td></tr>
              )}
              {!loading && depends.length === 0 && (
                <tr><td colSpan={6} className="px-3 py-4 text-center text-foreground/60">This frame has no dependencies.</td></tr>
              )}
              {!loading && depends.map((d, i) => (
                <tr key={d.id ?? i} className="border-t border-input/60">
                  <td className="px-3 py-1.5 font-mono">{d.type ?? ""}</td>
                  <td className="px-3 py-1.5 font-mono">{d.target ?? ""}</td>
                  <td className="px-3 py-1.5 font-mono">{d.active === undefined ? "" : String(d.active)}</td>
                  <td className="px-3 py-1.5 break-all font-mono">{onJobOf(d)}</td>
                  <td className="px-3 py-1.5 break-all font-mono">{onLayerOf(d)}</td>
                  <td className="px-3 py-1.5 break-all font-mono">{onFrameOf(d)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => frame && load(frame)} disabled={loading || !frame}>Refresh</Button>
          <Button onClick={() => setOpen(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Preview All: CueGUI renders the layer's output images. A browser can't do
// that, so we surface the layer's registered output paths instead so the user
// can locate the rendered frames.
function FramePreviewDialog({ job }: { job?: Job }) {
  const [open, setOpen] = React.useState(false);
  const [frame, setFrame] = React.useState<Frame | null>(null);
  const [paths, setPaths] = React.useState<string[]>([]);
  const [loading, setLoading] = React.useState(false);

  const load = React.useCallback(
    async (f: Frame) => {
      if (!job) return;
      setLoading(true);
      try {
        const layers = await getLayersForJob(job);
        const layer = layers.find((l) => l.name === f.layerName);
        setPaths(layer ? await fetchLayerOutputPaths(layer) : []);
      } catch (error) {
        handleError(error, "Could not load output paths");
      } finally {
        setLoading(false);
      }
    },
    [job],
  );

  React.useEffect(() => {
    function handler(e: Event) {
      const f = frameOf(e);
      if (!f) return;
      setFrame(f);
      setPaths([]);
      setOpen(true);
      load(f);
    }
    window.addEventListener("cueweb:open-frame-preview", handler);
    return () => window.removeEventListener("cueweb:open-frame-preview", handler);
  }, [load]);

  const ctx = {
    paths,
    job: job?.name ?? "",
    layer: frame?.layerName ?? "",
    frame: frame?.name ?? "",
  };
  const command = frame ? fillTemplate(PREVIEW_COMMAND_TEMPLATE, ctx, false) : "";

  async function copyCommand() {
    try {
      await navigator.clipboard.writeText(command);
      toastSuccess("Command copied");
    } catch (error) {
      handleError(error, "Could not copy to clipboard");
    }
  }

  function launch() {
    if (!frame || !PREVIEW_URL_TEMPLATE) return;
    window.location.href = fillTemplate(PREVIEW_URL_TEMPLATE, ctx, true);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Preview All</DialogTitle>
          <DialogDescription>
            Open the rendered frames for layer <span className="font-mono">{frame?.layerName}</span>{" "}
            in your image viewer. A browser can&apos;t display the frames itself, so the command
            below is run on your workstation (or launched via a registered URL handler).
          </DialogDescription>
        </DialogHeader>
        <div className="min-w-0 space-y-3 py-1 text-sm">
          <div>
            <span className="text-muted-foreground">Command</span>
            <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap break-all rounded-md border bg-muted/40 p-3 font-mono text-xs">
              {command || "(no preview command configured)"}
            </pre>
          </div>
          <div>
            <span className="text-muted-foreground">Output paths</span>
            <div className="mt-1 max-h-[35vh] min-w-0 overflow-auto rounded-md border border-input p-3 text-xs">
              {loading ? (
                <p className="text-foreground/60">Loading output paths...</p>
              ) : paths.length === 0 ? (
                <p className="text-foreground/60">
                  No output paths registered yet (frames may not have rendered).
                </p>
              ) : (
                <ul className="space-y-1">
                  {paths.map((p, i) => (
                    <li key={i} className="break-all font-mono">{p}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          {!PREVIEW_URL_TEMPLATE ? (
            <p className="text-xs text-muted-foreground">
              Set NEXT_PUBLIC_PREVIEW_URL to a registered URL scheme (e.g. a viewer like
              <span className="font-mono"> openrv://{"{paths}"}</span>) to enable the Launch button.
            </p>
          ) : null}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Close</Button>
          <Button variant="outline" onClick={copyCommand} disabled={!command}>Copy command</Button>
          <Button onClick={() => { launch(); setOpen(false); }} disabled={!PREVIEW_URL_TEMPLATE}>
            Launch
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// View Processes (CueGUI viewProcesses): the running frames in this frame's
// layer, with host + runtime. Frames are fetched from the parent job.
function FrameProcessesDialog({ job }: { job?: Job }) {
  const [open, setOpen] = React.useState(false);
  const [frame, setFrame] = React.useState<Frame | null>(null);
  const [frames, setFrames] = React.useState<Frame[]>([]);
  const [loading, setLoading] = React.useState(false);

  const load = React.useCallback(
    async (f: Frame) => {
      if (!job) return;
      setLoading(true);
      try {
        const all = await getFramesForJob(job);
        setFrames(all.filter((x) => x.layerName === f.layerName && x.state === "RUNNING"));
      } catch (error) {
        handleError(error, "Could not load processes");
      } finally {
        setLoading(false);
      }
    },
    [job],
  );

  React.useEffect(() => {
    function handler(e: Event) {
      const f = frameOf(e);
      if (!f) return;
      setFrame(f);
      setFrames([]);
      setOpen(true);
      load(f);
    }
    window.addEventListener("cueweb:open-frame-processes", handler);
    return () => window.removeEventListener("cueweb:open-frame-processes", handler);
  }, [load]);

  const nowSec = Math.floor(Date.now() / 1000);
  const hostOf = (f: Frame) => (f.lastResource ? f.lastResource.split("/")[0] : "-");

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>
            <span className="break-all font-mono">Processes: {frame?.layerName ?? ""}</span>
          </DialogTitle>
          <DialogDescription>Running frames in this frame&apos;s layer.</DialogDescription>
        </DialogHeader>
        <div className="max-h-[55vh] overflow-auto rounded-md border border-input text-xs">
          <table className="w-full table-auto">
            <thead className="sticky top-0 bg-foreground/[0.04]">
              <tr className="text-left">
                <th className="px-3 py-2">Frame</th>
                <th className="px-3 py-2">State</th>
                <th className="px-3 py-2">Host</th>
                <th className="px-3 py-2">Runtime</th>
                <th className="px-3 py-2">Memory</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={5} className="px-3 py-4 text-center text-foreground/60">Loading processes...</td></tr>
              )}
              {!loading && frames.length === 0 && (
                <tr><td colSpan={5} className="px-3 py-4 text-center text-foreground/60">No running frames in this layer.</td></tr>
              )}
              {!loading && frames.map((f) => (
                <tr key={f.id} className="border-t border-input/60">
                  <td className="px-3 py-1.5 break-all font-mono">{f.name}</td>
                  <td className="px-3 py-1.5"><Status status={f.state} /></td>
                  <td className="px-3 py-1.5 break-all font-mono">{hostOf(f)}</td>
                  <td className="px-3 py-1.5 font-mono">{f.startTime ? secondsToHHMMSS(Math.max(0, nowSec - f.startTime)) : "-"}</td>
                  <td className="px-3 py-1.5 font-mono">{convertMemoryToString(Number.parseInt(f.usedMemory), JSON.stringify(f))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => frame && load(frame)} disabled={loading || !frame || !job}>Refresh</Button>
          <Button onClick={() => setOpen(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Mounts every frame-menu dialog once. Place on any page that renders a frames
// table (Monitor Jobs inline panel, job detail Frames tab, frame log page).
// `job` powers Mark done / Eat and Mark done, Reorder, Preview All, View
// Processes and the frame Dependency Wizard.
export function FrameExtraDialogs({ job }: { job?: Job }) {
  // A frame's "Dependency Wizard..." reuses the full job Dependency Wizard,
  // preselected to FRAME_ON_FRAME. Bridge the frame-scoped event to the
  // wizard's open event. The wizard itself is mounted once per page (by the
  // jobs data-table or the job detail page) - do NOT mount another here.
  React.useEffect(() => {
    function handler() {
      if (!job) return;
      window.dispatchEvent(
        new CustomEvent(OPEN_DEPENDENCY_WIZARD_EVENT, {
          detail: { job, initialType: "FRAME_ON_FRAME" },
        }),
      );
    }
    window.addEventListener("cueweb:open-frame-depend-wizard", handler);
    return () => window.removeEventListener("cueweb:open-frame-depend-wizard", handler);
  }, [job]);

  return (
    <>
      <FrameReorderDialog job={job} />
      <FrameConfirmDialog job={job} />
      <FrameDependenciesDialog />
      <FramePreviewDialog job={job} />
      <FrameProcessesDialog job={job} />
    </>
  );
}
