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
import { usePathname } from "next/navigation";

import { trackPage } from "@/app/utils/usage_tracking";

// Mounted once from the root layout. Emits a usage page-view beacon whenever the
// route changes (deduped per pathname so a polling re-render doesn't inflate
// counts). Renders nothing.
export function UsageTracker() {
  const pathname = usePathname();
  const lastRef = React.useRef<string | null>(null);

  React.useEffect(() => {
    if (!pathname || pathname === lastRef.current) return;
    lastRef.current = pathname;
    // Don't count the login page as a module view; it gets its own login beacon.
    if (!pathname.startsWith("/login")) trackPage(pathname);
  }, [pathname]);

  return null;
}
