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

"use client";

import * as React from "react";
import { Copy, ExternalLink } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useCuebotFacility } from "@/app/utils/use_cuebot_facility";
import { toastSuccess, toastWarning } from "@/app/utils/notify_utils";

/**
 * "About CueWeb" dialog - CueGUI parity (Help -> About in
 * `cuegui/cuegui/MainWindow.py`). Opened from the Help menu via the
 * `CUEWEB_OPEN_ABOUT_EVENT` CustomEvent and mounted once at the layout level.
 *
 * Shows the build version + Git SHA (build-time env), the active Cuebot
 * facility, the REST gateway URL (masked so it can be pasted into a bug report
 * without leaking the full internal host), the license, and credits. A
 * "Copy diagnostics" button copies all fields as JSON.
 */

export const CUEWEB_OPEN_ABOUT_EVENT = "cueweb:open-about";

const LICENSE_URL =
  "https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/LICENSE";
const OPENCUE_URL = "https://www.opencue.io/";

/**
 * Mask a gateway URL for display: keep the scheme + port and the first/last
 * couple of host characters, replacing the middle with asterisks. Drops any
 * path / query / userinfo. Falls back to a coarse mask for non-URL strings.
 */
function maskGatewayUrl(raw: string | undefined): string {
  const value = (raw ?? "").trim();
  if (!value) return "(not configured)";
  try {
    const u = new URL(value);
    const host = u.hostname;
    const masked =
      host.length <= 4
        ? "*".repeat(host.length || 4)
        : `${host.slice(0, 2)}${"*".repeat(Math.max(3, host.length - 4))}${host.slice(-2)}`;
    const port = u.port ? `:${u.port}` : "";
    return `${u.protocol}//${masked}${port}`;
  } catch {
    return value.length <= 6 ? "******" : `${value.slice(0, 3)}***${value.slice(-3)}`;
  }
}

function Field({ label, value, mono = false }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="grid grid-cols-[8rem_1fr] items-start gap-2 py-1 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className={mono ? "break-all font-mono text-xs" : "break-words"}>{value}</dd>
    </div>
  );
}

export function AboutDialog() {
  const [open, setOpen] = React.useState(false);
  const { facility } = useCuebotFacility();

  React.useEffect(() => {
    const handler = () => setOpen(true);
    window.addEventListener(CUEWEB_OPEN_ABOUT_EVENT, handler);
    return () => window.removeEventListener(CUEWEB_OPEN_ABOUT_EVENT, handler);
  }, []);

  const version =
    process.env.NEXT_PUBLIC_APP_VERSION && process.env.NEXT_PUBLIC_APP_VERSION.length > 0
      ? process.env.NEXT_PUBLIC_APP_VERSION
      : "dev";
  const gitSha =
    process.env.NEXT_PUBLIC_GIT_SHA && process.env.NEXT_PUBLIC_GIT_SHA.length > 0
      ? process.env.NEXT_PUBLIC_GIT_SHA
      : "unknown";
  const maskedGateway = maskGatewayUrl(process.env.NEXT_PUBLIC_OPENCUE_ENDPOINT);

  async function copyDiagnostics() {
    const payload = {
      product: "CueWeb",
      version,
      gitSha,
      facility,
      restGateway: maskedGateway,
      userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "",
      generatedAt: new Date().toISOString(),
    };
    const text = JSON.stringify(payload, null, 2);
    try {
      await navigator.clipboard.writeText(text);
      toastSuccess("Diagnostics copied to clipboard.");
    } catch {
      toastWarning("Could not copy to clipboard.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>About CueWeb</DialogTitle>
          <DialogDescription>
            The web-based interface for OpenCue.
          </DialogDescription>
        </DialogHeader>

        <dl className="divide-y divide-border">
          <Field label="Version" value={version} mono />
          <Field label="Build SHA" value={gitSha} mono />
          <Field label="Cuebot facility" value={<span className="uppercase">{facility}</span>} />
          <Field label="REST gateway" value={maskedGateway} mono />
          <Field
            label="License"
            value={
              <a
                href={LICENSE_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-primary hover:underline"
              >
                Apache License 2.0
                <ExternalLink className="h-3 w-3" aria-hidden="true" />
              </a>
            }
          />
          <Field
            label="Credits"
            value={
              <span>
                OpenCue is an open source project hosted by the{" "}
                <a
                  href="https://www.aswf.io/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  Academy Software Foundation
                </a>
                . Learn more at{" "}
                <a
                  href={OPENCUE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  opencue.io
                </a>
                .
              </span>
            }
          />
        </dl>

        <DialogFooter className="gap-2 sm:justify-between">
          <Button type="button" variant="outline" size="sm" onClick={copyDiagnostics}>
            <Copy className="mr-2 h-4 w-4" aria-hidden="true" />
            Copy diagnostics
          </Button>
          <Button type="button" size="sm" onClick={() => setOpen(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
