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

import type { MouseEvent } from "react";
import { Bell, BellRing } from "lucide-react";
import { useJobSubscriptions } from "@/app/utils/use_job_subscriptions";
import { toastSuccess, toastWarning } from "@/app/utils/notify_utils";

// Request the OS-level Notification permission directly here. The helper
// that used to live in subscription_utils was removed upstream when the
// poller switched to in-app toasts; we still want the optional desktop
// popup upgrade when the user explicitly subscribes, so we prompt inline.
type NotificationPermissionResult = "granted" | "denied" | "default" | "unsupported";

async function requestNotificationPermission(): Promise<NotificationPermissionResult> {
  if (typeof window === "undefined" || typeof Notification === "undefined") {
    return "unsupported";
  }
  if (Notification.permission === "granted" || Notification.permission === "denied") {
    return Notification.permission;
  }
  try {
    return await Notification.requestPermission();
  } catch {
    return "default";
  }
}

interface Props {
  jobId: string;
  jobName: string;
  jobState: string;
}

// Per-row bell button. Three visual states:
//   - Outline bell           : not subscribed   -> click to subscribe
//   - Filled bell            : subscribed       -> click to cancel
//   - Filled bell + green dot: notified         -> click to clear
export function SubscribeBell({ jobId, jobName, jobState }: Props) {
  const { store, subscribe, unsubscribe } = useJobSubscriptions();
  const entry = store[jobId];

  const isDisabled = !entry && jobState === "FINISHED";

  const handleClick = async (e: MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation(); // don't trigger the row's click-through to the job detail dialog
    if (entry) {
      unsubscribe(jobId);
      return;
    }

    // Subscription is a localStorage flag - it's useful on its own (the
    // bell turns into a notified-state pip when the job finishes, and the
    // poller fires an in-app toast). So we ALWAYS subscribe; the OS-level
    // permission is just an optional upgrade for desktop popups.
    subscribe(jobId, jobName);

    const permission = await requestNotificationPermission();
    if (permission === "granted") {
      toastSuccess(`Subscribed to "${jobName}" - you'll get a desktop popup when it finishes.`);
    } else if (permission === "denied") {
      toastWarning(
        `Subscribed to "${jobName}" (in-app only). Desktop popups are blocked - enable notifications for this site in your browser settings to also receive system popups.`,
      );
    } else {
      // "default" - user dismissed the prompt without choosing. Still
      // subscribed; they can retry from browser site settings later.
      toastSuccess(`Subscribed to "${jobName}" (in-app only).`);
    }
  };

  let icon, label;
  if (!entry) {
    icon = <Bell size={16} />;
    label = isDisabled ? "Job is already finished. No notification needed" : "Subscribe to completion notification";
  } else if (entry.notifiedAt === null) {
    icon = <BellRing size={16} className="fill-current" />;
    label = "Subscribed, click to cancel";
  } else {
    icon = (
      <span className="relative inline-block">
        <BellRing size={16} className="fill-current" />
        <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-green-500" />
      </span>
    );
    label = "Notification fired, click to clear";
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={isDisabled}
      title={label}
      aria-label={label}
      className={`inline-flex items-center justify-center p-1 ${
        isDisabled ? "cursor-not-allowed opacity-30" : "hover:opacity-70"
      }`}
    >
      {icon}
    </button>
  );
}
