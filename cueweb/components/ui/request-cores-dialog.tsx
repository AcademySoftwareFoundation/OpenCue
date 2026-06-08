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

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { Job } from "@/app/jobs/columns";
import type { Layer } from "@/app/layers/layer-columns";
import { getLayersForJob } from "@/app/utils/get_utils";
import { convertMemoryToString } from "@/app/utils/layers_frames_utils";

/**
 * "Request Cores..." dialog. Mounted once at the page level and opened in
 * response to a `cueweb:open-request-cores` CustomEvent dispatched from
 * the row context menu. Decoupled this way so the menu's free-function
 * handlers can stay free of component refs.
 *
 * UI mirrors CueGUI's RequestCoresDialog: it's an email composer where
 * the user asks the show's support team to allocate more cores to a
 * specific job. The body is auto-populated with the job name, group
 * folder, and a per-layer breakdown (Layer Name / Minimum Memory /
 * Min Cores) of the layers that still have frames waiting or running -
 * matching CueGUI's "Layers that have frames remaining" table.
 *
 * Browsers can't send SMTP directly, so the **Send** button hands the
 * filled-in fields to the user's default mail client via a `mailto:`
 * URL. From: is whatever the user's mail account is configured with.
 *
 * Defaults are configurable at build time:
 *
 *   NEXT_PUBLIC_EMAIL_DOMAIN                   - default "your.domain.com"
 *   NEXT_PUBLIC_EMAIL_REQUEST_CORES_SUFFIX     - the per-show support
 *                                                alias suffix. Defaults
 *                                                to "support" so
 *                                                addresses come out as
 *                                                <show>-support@<domain>.
 */

export const OPEN_REQUEST_CORES_EVENT = "cueweb:open-request-cores";

export type OpenRequestCoresDetail = {
  job: Job;
};

const EMAIL_DOMAIN = (
  process.env.NEXT_PUBLIC_EMAIL_DOMAIN ?? "your.domain.com"
).trim();
const SUPPORT_SUFFIX = (
  process.env.NEXT_PUBLIC_EMAIL_REQUEST_CORES_SUFFIX ?? "support"
).trim();

function supportAddress(show: string): string {
  // Match CueGUI's "<show>-support@domain" alias convention.
  const safeShow = show?.trim() || "support";
  return `${safeShow}-${SUPPORT_SUFFIX}@${EMAIL_DOMAIN}`;
}

function userAddress(user: string): string {
  const safeUser = user?.trim() || "you";
  return `${safeUser}@${EMAIL_DOMAIN}`;
}

function defaultSubject(jobName: string): string {
  return `Requesting Cores for ${jobName}`;
}

// Format the layer breakdown as a fixed-width text table so it stays
// readable in any mail client (no markdown, no HTML).
function formatLayerTable(layers: Layer[]): string {
  if (!layers.length) {
    return "(no layers currently have waiting or running frames)";
  }
  const header =
    "Layer Name".padEnd(36) +
    "Minimum Memory".padEnd(18) +
    "Min Cores";
  const lines = layers.map((l) => {
    const mem = convertMemoryToString(
      Number.parseInt(String(l.minMemory)),
      JSON.stringify(l),
    );
    return (
      (l.name ?? "").padEnd(36) +
      String(mem).padEnd(18) +
      String(l.minCores ?? "")
    );
  });
  return [header, ...lines].join("\n");
}

function buildPrelude(job: Job, layers: Layer[] | null): string {
  // Show data mirrors CueGUI's "Group (Folder)" line. The Job object
  // doesn't expose the group on every call site, so fall back to the
  // show when group isn't set.
  const group = (job as unknown as { group?: string }).group ?? job.show;
  const layerSection =
    layers === null
      ? "Loading layers..."
      : formatLayerTable(layers);
  return (
    "Requesting more cores for:\n" +
    `Job Name:       ${job.name}\n` +
    `Group (Folder): ${group}\n` +
    "\n" +
    "Layers that have frames remaining (waiting and running):\n" +
    "\n" +
    layerSection +
    "\n"
  );
}

export function RequestCoresDialog() {
  const { data: session } = useSession();
  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);
  const [layers, setLayers] = React.useState<Layer[] | null>(null);

  const [from, setFrom] = React.useState("");
  const [to, setTo] = React.useState("");
  const [cc, setCc] = React.useState("");
  const [bcc, setBcc] = React.useState("");
  const [subject, setSubject] = React.useState("");
  const [completionBy, setCompletionBy] = React.useState("");
  const [extraNotes, setExtraNotes] = React.useState("");

  React.useEffect(() => {
    let cancelled = false;
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenRequestCoresDetail>).detail;
      if (!detail?.job) return;
      const j = detail.job;
      const sessionEmail =
        session?.user?.email ??
        (session?.user?.name ? userAddress(String(session.user.name)) : "");
      setJob(j);
      setFrom(sessionEmail || "");
      setTo("");
      setCc(supportAddress(j.show));
      setBcc("");
      setSubject(defaultSubject(j.name));
      setCompletionBy("");
      setExtraNotes("");
      setLayers(null);
      setOpen(true);
      // Fetch the layer breakdown asynchronously - keep the prelude in
      // "Loading layers..." until the response lands, then re-render
      // with the real table.
      getLayersForJob(j)
        .then((all) => {
          if (cancelled) return;
          const remaining = (all ?? []).filter((l) => {
            const w = l.layerStats?.waitingFrames ?? 0;
            const r = l.layerStats?.runningFrames ?? 0;
            return w + r > 0;
          });
          setLayers(remaining);
        })
        .catch(() => {
          if (!cancelled) setLayers([]);
        });
    }
    window.addEventListener(OPEN_REQUEST_CORES_EVENT, handler);
    return () => {
      cancelled = true;
      window.removeEventListener(OPEN_REQUEST_CORES_EVENT, handler);
    };
  }, [session?.user?.email, session?.user?.name]);

  function handleSend() {
    if (!job) return;
    // Stitch the user-filled sections onto the auto-populated prelude.
    const body =
      buildPrelude(job, layers) +
      "\n" +
      "Date/Time by which completion is needed:\n" +
      (completionBy.trim() || "(not specified)") +
      "\n\n" +
      "Additional notes (flag priority frames etc.):\n" +
      (extraNotes.trim() || "(none)") +
      "\n";

    const params = new URLSearchParams();
    if (cc.trim()) params.set("cc", cc.trim());
    if (bcc.trim()) params.set("bcc", bcc.trim());
    if (subject) params.set("subject", subject);
    if (body) params.set("body", body);
    // URLSearchParams encodes spaces as "+", but per RFC 6068 mailto: URIs
    // do NOT decode "+" as space - only "%20" is treated that way - so
    // every space in the subject and body (including the padEnd spaces
    // that align the Layer Name / Minimum Memory / Min Cores columns)
    // would arrive as a literal "+" character in the user's mail client.
    // Normalize before handing the URL to the browser.
    const qs = params.toString().replace(/\+/g, "%20");
    const url = qs
      ? `mailto:${encodeURIComponent(to.trim())}?${qs}`
      : `mailto:${encodeURIComponent(to.trim())}`;
    window.location.href = url;
    setOpen(false);
  }

  const inputClass =
    "flex-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm";

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            <span className="font-mono break-all">
              Request Cores For: {job?.name ?? "Job"}
            </span>
          </DialogTitle>
          <DialogDescription>
            Send opens your default mail client with these fields filled in.
            The actual <span className="font-mono">From:</span> header is
            whatever your mail client is configured with.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-2 py-2 text-sm">
          {[
            ["From:", from, setFrom, "request-cores-from"],
            ["To:", to, setTo, "request-cores-to"],
            ["CC:", cc, setCc, "request-cores-cc"],
            ["BCC:", bcc, setBcc, "request-cores-bcc"],
            ["Subject:", subject, setSubject, "request-cores-subject"],
          ].map(([label, value, set, id]) => (
            <div key={id as string} className="flex items-center gap-3">
              <label
                htmlFor={id as string}
                className="w-20 shrink-0 text-right text-foreground/70"
              >
                {label as string}
              </label>
              <input
                id={id as string}
                type="text"
                value={value as string}
                onChange={(e) =>
                  (set as React.Dispatch<React.SetStateAction<string>>)(
                    e.target.value,
                  )
                }
                className={inputClass}
              />
            </div>
          ))}

          <pre
            aria-label="Auto-populated message body"
            className="mt-2 max-h-60 overflow-auto whitespace-pre-wrap rounded-md border border-input bg-foreground/[0.04] p-3 font-mono text-xs leading-relaxed text-foreground/90"
          >
            {job ? buildPrelude(job, layers) : ""}
          </pre>

          <label
            htmlFor="request-cores-completion"
            className="mt-2 text-foreground/70"
          >
            Add Date/Time by which completion is needed:
          </label>
          <textarea
            id="request-cores-completion"
            value={completionBy}
            onChange={(e) => setCompletionBy(e.target.value)}
            rows={3}
            placeholder="e.g. Tomorrow 10:00 PST, by EOD Friday, ..."
            className="w-full rounded-md border border-input bg-background p-3 text-sm leading-relaxed"
          />

          <label
            htmlFor="request-cores-notes"
            className="mt-2 text-foreground/70"
          >
            Add any additional notes (flag priority frames etc.):
          </label>
          <textarea
            id="request-cores-notes"
            value={extraNotes}
            onChange={(e) => setExtraNotes(e.target.value)}
            rows={4}
            placeholder="e.g. Priority frames 1-10. Memory floor can be raised to 4G if it helps."
            className="w-full rounded-md border border-input bg-background p-3 text-sm leading-relaxed"
          />
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => setOpen(false)}
          >
            Cancel
          </Button>
          <Button type="button" onClick={handleSend} disabled={!to.trim()}>
            Send
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
