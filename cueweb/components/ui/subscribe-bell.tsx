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

import { Bell, BellRing } from "lucide-react";
import { useJobSubscriptions } from "@/app/utils/use_job_subscriptions";
import { requestNotificationPermission } from "@/app/utils/subscription_utils";
import { toastWarning } from "@/app/utils/notify_utils";

interface Props {
  jobId: string;
  jobName: string;
  jobState: string;
}

// Per-row bell button. Three visual states:
//   - Outline bell           : not subscribed   → click to subscribe
//   - Filled bell            : subscribed       → click to cancel
//   - Filled bell + green dot: notified         → click to clear
export function SubscribeBell({ jobId, jobName, jobState }: Props) {
  const { store, subscribe, unsubscribe } = useJobSubscriptions();
  const entry = store[jobId];

  const isDisabled = !entry && jobState === "FINISHED";

  const handleClick = async (e: React.MouseEvent) => {
    e.stopPropagation(); // don't trigger the row's click-through to the job detail dialog

    if (entry) {
      unsubscribe(jobId);
      return;
    }

    const permission = await requestNotificationPermission();
    if (permission !== "granted") {
      toastWarning("Browser notifications denied. Enable in browser settings to subscribe.");
      return;
    }

    subscribe(jobId, jobName);
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
