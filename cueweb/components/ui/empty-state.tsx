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

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface EmptyStateAction {
  label: string;
  onClick: () => void;
}

export interface EmptyStateProps {
  /** Visual leading icon - typically a lucide-react element. */
  icon: React.ReactNode;
  /** Bold one-line heading, e.g. "No jobs monitored". */
  title: string;
  /** Supporting copy below the heading. */
  description: string;
  /** Optional CTA rendered as an outline button. */
  action?: EmptyStateAction;
  className?: string;
}

/**
 * Reusable empty-state placeholder. Centered icon + heading + description
 * + optional CTA. Themed via Tailwind semantic tokens so it reads on both
 * light and dark surfaces without overriding callers.
 */
export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "flex w-full flex-col items-center justify-center gap-2 px-6 py-10 text-center",
        className,
      )}
    >
      <div
        aria-hidden="true"
        className="mb-1 inline-flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground"
      >
        {icon}
      </div>
      <p className="text-base font-semibold text-foreground">{title}</p>
      <p className="max-w-md text-sm text-muted-foreground">{description}</p>
      {action && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={action.onClick}
          className="mt-3"
        >
          {action.label}
        </Button>
      )}
    </div>
  );
}
