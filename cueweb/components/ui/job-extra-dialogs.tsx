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
import { useSession } from "next-auth/react";

import type { Job } from "@/app/jobs/columns";
import {
  addRenderPartition,
  reorderJobFrames,
  setJobMaxCores,
  setJobMaxGpus,
  setJobMaxRetries,
  setJobMinCores,
  setJobMinGpus,
  setJobUserColor,
  staggerJobFrames,
} from "@/app/utils/action_utils";
import { handleError, toastSuccess, toastWarning } from "@/app/utils/notify_utils";
import { CUEGUI_USER_COLORS, CUEWEB_BRIGHT_COLORS } from "@/app/utils/user_colors";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

const KB_PER_GB = 1048576;
const SELECT_CLASS =
  "h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

type ScalarField = "minCores" | "maxCores" | "minGpus" | "maxGpus" | "maxRetries";
const SCALAR_LABEL: Record<ScalarField, string> = {
  minCores: "Minimum Cores",
  maxCores: "Maximum Cores",
  minGpus: "Minimum GPUs",
  maxGpus: "Maximum GPUs",
  maxRetries: "Max Retries",
};

function SetJobScalarDialog() {
  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);
  const [field, setField] = React.useState<ScalarField>("minCores");
  const [value, setValue] = React.useState("0");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const d = (e as CustomEvent<{ job: Job; field: ScalarField }>).detail;
      setJob(d.job);
      setField(d.field);
      setValue(String((d.job as Record<string, unknown>)[d.field] ?? 0));
      setOpen(true);
    }
    window.addEventListener("cueweb:open-set-job-scalar", handler);
    return () => window.removeEventListener("cueweb:open-set-job-scalar", handler);
  }, []);

  async function apply() {
    if (!job) return;
    const n = Number(value);
    if (!Number.isFinite(n) || n < 0) {
      toastWarning(`${SCALAR_LABEL[field]} must be a non-negative number.`);
      return;
    }
    // GPUs and retries are int32 in the proto; only cores accept fractions.
    const requiresInteger = field === "minGpus" || field === "maxGpus" || field === "maxRetries";
    if (requiresInteger && !Number.isInteger(n)) {
      toastWarning(`${SCALAR_LABEL[field]} must be a non-negative integer.`);
      return;
    }
    setBusy(true);
    try {
      const fn =
        field === "minCores" ? setJobMinCores
        : field === "maxCores" ? setJobMaxCores
        : field === "minGpus" ? setJobMinGpus
        : field === "maxGpus" ? setJobMaxGpus
        : setJobMaxRetries;
      if (await fn(job, n)) setOpen(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={busy ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Set {SCALAR_LABEL[field]}</DialogTitle>
        </DialogHeader>
        <div className="space-y-1 py-2">
          <p className="break-all font-mono text-xs text-muted-foreground" title={job?.name}>{job?.name}</p>
          <Input type="number" min={0} step={field === "minCores" || field === "maxCores" ? "0.01" : "1"} value={value} onChange={(e) => setValue(e.target.value)} aria-label={SCALAR_LABEL[field]} autoFocus />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>Cancel</Button>
          <Button onClick={apply} disabled={busy}>OK</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ReorderFramesDialog() {
  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);
  const [range, setRange] = React.useState("");
  const [order, setOrder] = React.useState<"FIRST" | "LAST" | "REVERSE">("FIRST");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      setJob((e as CustomEvent<{ job: Job }>).detail.job);
      setRange("");
      setOrder("FIRST");
      setOpen(true);
    }
    window.addEventListener("cueweb:open-reorder-frames", handler);
    return () => window.removeEventListener("cueweb:open-reorder-frames", handler);
  }, []);

  async function apply() {
    if (!job) return;
    if (!range.trim()) {
      toastWarning("Enter a frame range (e.g. 1-100).");
      return;
    }
    setBusy(true);
    try {
      if (await reorderJobFrames(job, range.trim(), order)) setOpen(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={busy ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Reorder Frames</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <p className="break-all font-mono text-xs text-muted-foreground" title={job?.name}>{job?.name}</p>
          <label className="block text-sm">
            <span className="text-muted-foreground">Frame range</span>
            <Input value={range} onChange={(e) => setRange(e.target.value)} placeholder="1-100" aria-label="Frame range" />
          </label>
          <label className="block text-sm">
            <span className="text-muted-foreground">Order</span>
            <select value={order} onChange={(e) => setOrder(e.target.value as any)} className={SELECT_CLASS} aria-label="Order">
              <option value="FIRST">First</option>
              <option value="LAST">Last</option>
              <option value="REVERSE">Reverse</option>
            </select>
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>Cancel</Button>
          <Button onClick={apply} disabled={busy}>OK</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function StaggerFramesDialog() {
  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);
  const [range, setRange] = React.useState("");
  const [stagger, setStagger] = React.useState("1");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      setJob((e as CustomEvent<{ job: Job }>).detail.job);
      setRange("");
      setStagger("1");
      setOpen(true);
    }
    window.addEventListener("cueweb:open-stagger-frames", handler);
    return () => window.removeEventListener("cueweb:open-stagger-frames", handler);
  }, []);

  async function apply() {
    if (!job) return;
    const inc = Number(stagger);
    if (!range.trim()) {
      toastWarning("Enter a frame range (e.g. 1-100).");
      return;
    }
    if (!Number.isInteger(inc) || inc < 1) {
      toastWarning("Stagger must be a positive integer.");
      return;
    }
    setBusy(true);
    try {
      if (await staggerJobFrames(job, range.trim(), inc)) setOpen(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={busy ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Stagger Frames</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <p className="break-all font-mono text-xs text-muted-foreground" title={job?.name}>{job?.name}</p>
          <label className="block text-sm">
            <span className="text-muted-foreground">Frame range</span>
            <Input value={range} onChange={(e) => setRange(e.target.value)} placeholder="1-100" aria-label="Frame range" />
          </label>
          <label className="block text-sm">
            <span className="text-muted-foreground">Stagger by</span>
            <Input type="number" min={1} step={1} value={stagger} onChange={(e) => setStagger(e.target.value)} aria-label="Stagger" />
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>Cancel</Button>
          <Button onClick={apply} disabled={busy}>OK</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function UseLocalCoresDialog() {
  const { data: session } = useSession();
  const username = session?.user?.name ?? session?.user?.email?.split("@")[0] ?? "";
  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);
  const [host, setHost] = React.useState("");
  const [cores, setCores] = React.useState("1");
  const [memGb, setMemGb] = React.useState("4");
  const [gpus, setGpus] = React.useState("0");
  const [gpuMemGb, setGpuMemGb] = React.useState("0");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      setJob((e as CustomEvent<{ job: Job }>).detail.job);
      setHost("");
      setCores("1");
      setMemGb("4");
      setGpus("0");
      setGpuMemGb("0");
      setOpen(true);
    }
    window.addEventListener("cueweb:open-use-local-cores", handler);
    return () => window.removeEventListener("cueweb:open-use-local-cores", handler);
  }, []);

  async function apply() {
    if (!job) return;
    if (!host.trim()) {
      toastWarning("Enter the host to book.");
      return;
    }
    // threads/maxCores and maxGpus are int32; the GB inputs may be fractional
    // (rounded into int64 KB below). Validate before building the payload so a
    // NaN can't serialize to null and produce a malformed request.
    const c = Number(cores);
    const mem = Number(memGb);
    const g = Number(gpus);
    const gpuMem = Number(gpuMemGb);
    if (!Number.isInteger(c) || c < 1) {
      toastWarning("Cores must be a positive integer.");
      return;
    }
    if (!Number.isFinite(mem) || mem < 0) {
      toastWarning("Memory must be a non-negative number.");
      return;
    }
    if (!Number.isInteger(g) || g < 0) {
      toastWarning("GPUs must be a non-negative integer.");
      return;
    }
    if (!Number.isFinite(gpuMem) || gpuMem < 0) {
      toastWarning("GPU memory must be a non-negative number.");
      return;
    }
    setBusy(true);
    try {
      const ok = await addRenderPartition(job, {
        host: host.trim(),
        username,
        threads: c,
        maxCores: c,
        maxMemory: Math.round(mem * KB_PER_GB),
        maxGpus: g,
        maxGpuMemory: Math.round(gpuMem * KB_PER_GB),
      });
      if (ok) setOpen(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={busy ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Use Local Cores</DialogTitle>
        </DialogHeader>
        <div className="min-w-0 space-y-3 py-2 text-sm">
          <p className="break-all font-mono text-xs text-muted-foreground">{job?.name}</p>
          <p className="text-xs text-muted-foreground">
            Book a host&apos;s resources to this job (adds a render partition). The host must be
            NIMBY-locked first.
          </p>
          <label className="block min-w-0">
            <span className="text-muted-foreground">Host</span>
            <Input value={host} onChange={(e) => setHost(e.target.value)} placeholder="hostname" aria-label="Host" className="w-full" />
          </label>
          <div className="grid min-w-0 grid-cols-2 gap-3">
            <label className="block min-w-0">
              <span className="text-muted-foreground">Cores</span>
              <Input type="number" min={1} value={cores} onChange={(e) => setCores(e.target.value)} aria-label="Cores" className="w-full" />
            </label>
            <label className="block min-w-0">
              <span className="text-muted-foreground">Memory (GB)</span>
              <Input type="number" min={0} step={0.5} value={memGb} onChange={(e) => setMemGb(e.target.value)} aria-label="Memory GB" className="w-full" />
            </label>
            <label className="block min-w-0">
              <span className="text-muted-foreground">GPUs</span>
              <Input type="number" min={0} value={gpus} onChange={(e) => setGpus(e.target.value)} aria-label="GPUs" className="w-full" />
            </label>
            <label className="block min-w-0">
              <span className="text-muted-foreground">GPU Memory (GB)</span>
              <Input type="number" min={0} step={0.5} value={gpuMemGb} onChange={(e) => setGpuMemGb(e.target.value)} aria-label="GPU Memory GB" className="w-full" />
            </label>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>Cancel</Button>
          <Button onClick={apply} disabled={busy}>OK</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function SetUserColorDialog() {
  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);
  const [color, setColor] = React.useState(CUEGUI_USER_COLORS[0].hex);

  React.useEffect(() => {
    function handler(e: Event) {
      setJob((e as CustomEvent<{ job: Job }>).detail.job);
      setOpen(true);
    }
    window.addEventListener("cueweb:open-user-color", handler);
    return () => window.removeEventListener("cueweb:open-user-color", handler);
  }, []);

  function apply() {
    if (!job) return;
    setJobUserColor(job.id, color);
    toastSuccess(`Set user color on ${job.name}`);
    setOpen(false);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Set User Color</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div className="space-y-1.5">
            <span className="text-xs font-medium text-muted-foreground">CueGUI colors</span>
            <div className="grid grid-cols-5 gap-2">
              {CUEGUI_USER_COLORS.map((c, i) => (
                <button
                  key={c.hex}
                  onClick={() => setColor(c.hex)}
                  className={`h-7 w-full rounded border ${color === c.hex ? "ring-2 ring-ring" : "border-border"}`}
                  style={{ backgroundColor: c.hex }}
                  aria-label={`Set Color ${i + 1} - ${c.name}`}
                  title={`Set Color ${i + 1} - ${c.name}`}
                />
              ))}
            </div>
          </div>
          <div className="space-y-1.5">
            <span className="text-xs font-medium text-muted-foreground">Bright colors</span>
            <div className="grid grid-cols-5 gap-2">
              {CUEWEB_BRIGHT_COLORS.map((c) => (
                <button
                  key={c.hex}
                  onClick={() => setColor(c.hex)}
                  className={`h-7 w-full rounded border ${color === c.hex ? "ring-2 ring-ring" : "border-border"}`}
                  style={{ backgroundColor: c.hex }}
                  aria-label={c.name}
                  title={c.name}
                />
              ))}
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Custom</span>
            <input type="color" value={color} onChange={(e) => setColor(e.target.value)} className="h-7 w-10 cursor-pointer rounded border border-border bg-transparent p-0" aria-label="Custom color" />
            <span className="font-mono text-xs">{color}</span>
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={apply}>OK</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// "Show Progress Bar" dialog. Shows the configured CueProgBar command for the
// job and offers Copy + Launch. The command template is configurable via
// NEXT_PUBLIC_CUEPROGBAR_COMMAND (e.g. "python -m cuegui.cueguiplugin.cueprogbar
// {job}" or "spawn launch cueprogbar {job}"); {job} is replaced with the job
// name. Launch hands off to the NEXT_PUBLIC_CUEPROGBAR_URL scheme (a browser
// can't spawn a local process), which the workstation's URL handler runs.
const CUEPROGBAR_COMMAND_TEMPLATE = (
  process.env.NEXT_PUBLIC_CUEPROGBAR_COMMAND ?? "python -m cuegui.cueguiplugin.cueprogbar {job}"
).trim();
const CUEPROGBAR_URL_TEMPLATE = (process.env.NEXT_PUBLIC_CUEPROGBAR_URL ?? "").trim();

function CueProgBarDialog() {
  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);

  React.useEffect(() => {
    function handler(e: Event) {
      setJob((e as CustomEvent<{ job: Job }>).detail.job);
      setOpen(true);
    }
    window.addEventListener("cueweb:open-cueprogbar", handler);
    return () => window.removeEventListener("cueweb:open-cueprogbar", handler);
  }, []);

  const command = job ? CUEPROGBAR_COMMAND_TEMPLATE.replace(/\{job\}/g, job.name) : "";

  async function copyCommand() {
    try {
      await navigator.clipboard.writeText(command);
      toastSuccess("Command copied");
    } catch (error) {
      handleError(error, "Could not copy to clipboard");
    }
  }

  function launch() {
    if (!job || !CUEPROGBAR_URL_TEMPLATE) return;
    window.location.href = CUEPROGBAR_URL_TEMPLATE.replace(/\{job\}/g, encodeURIComponent(job.name));
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Show Progress Bar</DialogTitle>
        </DialogHeader>
        <div className="min-w-0 space-y-3 py-2 text-sm">
          <p className="break-all font-mono text-xs text-muted-foreground">{job?.name}</p>
          <div>
            <span className="text-muted-foreground">Command</span>
            <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-all rounded-md border bg-muted/40 p-3 font-mono text-xs">
              {command}
            </pre>
          </div>
          {!CUEPROGBAR_URL_TEMPLATE ? (
            <p className="text-xs text-muted-foreground">
              CueProgBar is a desktop tool. Run the command above on your workstation, or set
              NEXT_PUBLIC_CUEPROGBAR_URL to a registered URL scheme to enable the Launch button.
            </p>
          ) : null}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Close</Button>
          <Button variant="outline" onClick={copyCommand}>Copy command</Button>
          <Button onClick={() => { launch(); setOpen(false); }} disabled={!CUEPROGBAR_URL_TEMPLATE}>
            Launch
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Mounts the additional CueGUI job-menu dialogs (Cuetopia + Monitor Cue).
export function JobExtraDialogs() {
  return (
    <>
      <SetJobScalarDialog />
      <ReorderFramesDialog />
      <StaggerFramesDialog />
      <UseLocalCoresDialog />
      <SetUserColorDialog />
      <CueProgBarDialog />
    </>
  );
}
