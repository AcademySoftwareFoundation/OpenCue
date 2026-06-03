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

/**
 * "Email Artist..." dialog. Mounted once at the page level and opened in
 * response to a `cueweb:open-email-artist` CustomEvent dispatched from the
 * row context menu. Decoupled this way so the menu's free-function
 * handlers can stay free of component refs.
 *
 * UI mirrors CueGUI's EmailDialog (cuegui.EmailDialog):
 *
 *   Email For: <jobName>
 *   From:    <show>-<support_suffix>@<domain>
 *   To:      <artist>@<domain>      (the job's user)
 *   CC:      <show>-<support_suffix>@<domain>
 *   BCC:     (empty)
 *   Subject: cuemail: please check <jobName>
 *   Body:    Your Support Team requests that you check <jobName>
 *
 *            Hi <artist>,
 *
 *   [ Send ] [ Cancel ]
 *
 * Browsers can't send SMTP directly, so the **Send** button hands the
 * filled-in fields to the user's default mail client via a `mailto:` URL.
 * That means the actual From: header is whatever the user's mail account
 * is configured with - the From field in this dialog is informational
 * (it tells the user which alias the support team typically uses).
 *
 * Defaults are configurable at build time:
 *
 *   NEXT_PUBLIC_EMAIL_DOMAIN          - domain part of every address (no @).
 *                                       Defaults to "your.domain.com",
 *                                       matching CueGUI's placeholder.
 *   NEXT_PUBLIC_EMAIL_SUPPORT_SUFFIX  - the per-show support alias suffix.
 *                                       Defaults to "pst" (production
 *                                       support team) so addresses come out
 *                                       as <show>-pst@<domain>.
 */

export const OPEN_EMAIL_ARTIST_EVENT = "cueweb:open-email-artist";

export type OpenEmailArtistDetail = {
  job: Job;
};

const EMAIL_DOMAIN = (
  process.env.NEXT_PUBLIC_EMAIL_DOMAIN ?? "your.domain.com"
).trim();
const SUPPORT_SUFFIX = (
  process.env.NEXT_PUBLIC_EMAIL_SUPPORT_SUFFIX ?? "pst"
).trim();

function supportAddress(show: string): string {
  // Match CueGUI's "show-pst@domain" alias convention.
  const safeShow = show?.trim() || "support";
  return `${safeShow}-${SUPPORT_SUFFIX}@${EMAIL_DOMAIN}`;
}

function artistAddress(user: string): string {
  const safeUser = user?.trim() || "artist";
  return `${safeUser}@${EMAIL_DOMAIN}`;
}

function defaultSubject(jobName: string): string {
  return `cuemail: please check ${jobName}`;
}

function defaultBody(jobName: string, user: string): string {
  const safeUser = user?.trim() || "there";
  return `Your Support Team requests that you check ${jobName}\n\nHi ${safeUser},\n`;
}

export function EmailArtistDialog() {
  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);

  const [from, setFrom] = React.useState("");
  const [to, setTo] = React.useState("");
  const [cc, setCc] = React.useState("");
  const [bcc, setBcc] = React.useState("");
  const [subject, setSubject] = React.useState("");
  const [body, setBody] = React.useState("");

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenEmailArtistDetail>).detail;
      if (!detail?.job) return;
      const j = detail.job;
      const support = supportAddress(j.show);
      setJob(j);
      setFrom(support);
      setTo(artistAddress(j.user));
      setCc(support);
      setBcc("");
      setSubject(defaultSubject(j.name));
      setBody(defaultBody(j.name, j.user));
      setOpen(true);
    }
    window.addEventListener(OPEN_EMAIL_ARTIST_EVENT, handler);
    return () => window.removeEventListener(OPEN_EMAIL_ARTIST_EVENT, handler);
  }, []);

  function handleSend() {
    // Build a mailto: URL and let the OS hand it off to the user's
    // default mail client. The From: header is decided by that client
    // (mailto: can't override it); the rest of the fields populate the
    // composer window so the user only has to review and hit send.
    const params = new URLSearchParams();
    if (cc.trim()) params.set("cc", cc.trim());
    if (bcc.trim()) params.set("bcc", bcc.trim());
    if (subject) params.set("subject", subject);
    if (body) params.set("body", body);
    // URLSearchParams encodes spaces as "+", but per RFC 6068 mailto: URIs
    // do NOT decode "+" as space - only "%20" is treated that way - so
    // every space in the subject and body would arrive as a literal "+"
    // in the user's mail client. Normalize before handing the URL to
    // the browser.
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
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            <span className="font-mono break-all">
              Email For: {job?.name ?? "Job"}
            </span>
          </DialogTitle>
          <DialogDescription>
            Send opens your default mail client with these fields filled in.
            The actual <span className="font-mono">From:</span> header is
            whatever your mail client is configured with - the From field
            below is informational.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-2 py-2 text-sm">
          {[
            ["From:", from, setFrom, "email-artist-from"],
            ["To:", to, setTo, "email-artist-to"],
            ["CC:", cc, setCc, "email-artist-cc"],
            ["BCC:", bcc, setBcc, "email-artist-bcc"],
            ["Subject:", subject, setSubject, "email-artist-subject"],
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
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={10}
            aria-label="Email body"
            className="w-full rounded-md border border-input bg-background p-3 font-mono text-sm leading-relaxed"
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
