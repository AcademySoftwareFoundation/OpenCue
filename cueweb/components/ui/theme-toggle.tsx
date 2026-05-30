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
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";

// One-click theme toggle. The button shows the icon for the theme the
// user would switch TO, so a sun means "click to go light" (currently
// dark) and a moon means "click to go dark" (currently light).
//
// We read `resolvedTheme` so the toggle behaves correctly even when the
// user is on the "system" preference - it flips to the opposite of
// whatever is actually rendering, not the literal "system" string.
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();

  // SSR + first client render: `resolvedTheme` is undefined until the
  // next-themes ThemeProvider hydrates. We render an empty-but-sized
  // placeholder so the layout doesn't jump on hydration.
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);
  if (!mounted) {
    // disabled + tabIndex={-1} so the hydration placeholder doesn't briefly
    // act as a focus target / keyboard trap before the real toggle mounts.
    return (
      <Button variant="outline" size="icon" aria-hidden="true" disabled tabIndex={-1}>
        <span className="h-[1.2rem] w-[1.2rem]" />
      </Button>
    );
  }

  const isDark = resolvedTheme === "dark";
  const label = isDark ? "Switch to light theme" : "Switch to dark theme";

  return (
    <Button
      variant="outline"
      size="icon"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      title={label}
      aria-label={label}
    >
      {isDark ? (
        <Sun className="h-[1.2rem] w-[1.2rem]" />
      ) : (
        <Moon className="h-[1.2rem] w-[1.2rem]" />
      )}
    </Button>
  );
}
