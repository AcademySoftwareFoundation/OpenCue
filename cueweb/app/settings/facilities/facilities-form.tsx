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

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { FacilityConfigView } from "@/lib/facility";
import { updateFacilityConfig, type UpdateFacilityResult } from "./actions";

function FacilityRow({ view }: { view: FacilityConfigView }) {
  const [result, setResult] = React.useState<UpdateFacilityResult | null>(null);
  const [pending, startTransition] = React.useTransition();

  // Server actions are callable directly from client components (an RPC under
  // the hood). useTransition gives us the pending state without depending on
  // the React 19 form hooks (this app is on React 18.3).
  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const form = event.currentTarget;
    startTransition(async () => {
      const r = await updateFacilityConfig(null, formData);
      setResult(r);
      if (r.ok) {
        // Keep the gateway URL the user typed; just clear the secret inputs.
        const secret = form.elements.namedItem("jwtSecret") as HTMLInputElement | null;
        const clear = form.elements.namedItem("clearSecret") as HTMLInputElement | null;
        if (secret) secret.value = "";
        if (clear) clear.checked = false;
      }
    });
  }

  const sourceLabel =
    view.source === "override"
      ? "runtime override"
      : view.source === "env"
        ? "environment"
        : view.source === "default"
          ? "default gateway"
          : "not set";

  return (
    <form onSubmit={handleSubmit} className="rounded-md border border-border p-4">
      <input type="hidden" name="facility" value={view.name} />
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold uppercase tracking-wide">{view.name}</h3>
        <span className="text-xs text-muted-foreground">
          gateway from: <span className="font-medium">{sourceLabel}</span>
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs">
          <span className="font-medium text-foreground/80">REST gateway URL</span>
          <Input
            type="url"
            name="gatewayUrl"
            defaultValue={view.hasOverride ? view.gatewayUrl : ""}
            placeholder={view.gatewayUrl || "http://gateway:8448 (not set)"}
            className="h-8 text-xs"
          />
          <span className="text-[11px] text-muted-foreground">
            Leave blank to use the environment / default gateway.
          </span>
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span className="font-medium text-foreground/80">JWT secret</span>
          <Input
            type="password"
            name="jwtSecret"
            placeholder={view.hasJwtSecret ? "configured — leave blank to keep" : "not set"}
            autoComplete="new-password"
            className="h-8 text-xs"
          />
          <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <input type="checkbox" name="clearSecret" className="h-3 w-3" />
            Clear secret override{view.secretFromOverride ? "" : " (none set)"}
          </span>
        </label>
      </div>

      <div className="mt-3 flex items-center gap-3">
        <Button type="submit" size="sm" disabled={pending}>
          {pending ? "Saving…" : "Save"}
        </Button>
        {result && (
          <span
            className={`text-xs ${result.ok ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}
          >
            {result.message}
          </span>
        )}
      </div>
    </form>
  );
}

export function FacilitiesForm({ facilities }: { facilities: FacilityConfigView[] }) {
  return (
    <div className="flex flex-col gap-4">
      {facilities.map((view) => (
        <FacilityRow key={view.name} view={view} />
      ))}
    </div>
  );
}
