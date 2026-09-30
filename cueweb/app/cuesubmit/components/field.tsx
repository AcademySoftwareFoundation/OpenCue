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
import { cn } from "@/lib/utils";

// Shared field wrapper. The cuesubmit reference UI tints REQUIRED
// field labels red until they have a value; we mirror that to give
// users the same visual scan target.

export function Field({
  label,
  required,
  invalid,
  htmlFor,
  hint,
  className,
  children,
}: {
  label: string;
  required?: boolean;
  invalid?: boolean;
  htmlFor?: string;
  hint?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className={cn("flex flex-col gap-1 text-sm", className)}
    >
      <span
        className={cn(
          "font-medium",
          required && invalid
            ? "text-red-600 dark:text-red-400"
            : "text-foreground/80",
        )}
      >
        {label}
      </span>
      {children}
      {hint && (
        <span
          className={cn(
            "text-xs",
            invalid
              ? "text-red-600 dark:text-red-400"
              : "text-foreground/60",
          )}
        >
          {hint}
        </span>
      )}
    </label>
  );
}
