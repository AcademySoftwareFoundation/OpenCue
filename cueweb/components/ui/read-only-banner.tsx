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

import { Lock } from "lucide-react";
import { usePathname } from "next/navigation";

import { useDisableJobInteraction } from "@/app/utils/use_disable_job_interaction";

/**
 * Thin amber strip shown just under the AppHeader when "Disable Job
 * Interaction" is on. Lets users re-enable interaction from the banner.
 * Hidden on /login (no header there).
 */
export function ReadOnlyBanner() {
  const pathname = usePathname();
  const { disabled, setDisabled } = useDisableJobInteraction();

  if (pathname?.startsWith("/login")) return null;
  if (!disabled) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex w-full items-center justify-center gap-3 border-b border-amber-500/50 bg-amber-100 px-4 py-2 text-sm text-amber-900 dark:bg-amber-900/30 dark:text-amber-200"
    >
      <Lock className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span>
        <strong>Job interaction is disabled.</strong> Destructive actions
        (pause, unpause, retry, kill, eat) are hidden or disabled until you
        re-enable them.
      </span>
      <button
        type="button"
        onClick={() => setDisabled(false)}
        className="ml-2 rounded-md border border-amber-600/50 px-2 py-0.5 text-xs font-medium text-amber-900 hover:bg-amber-200/50 dark:text-amber-100 dark:hover:bg-amber-800/40"
      >
        Re-enable
      </button>
    </div>
  );
}
