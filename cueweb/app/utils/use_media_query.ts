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

/**
 * Subscribes to a CSS media query and returns its current match state.
 *
 * SSR-safe: returns `false` on the server and on the first client render so
 * the rendered DOM is stable; the real value is read in an effect to avoid
 * hydration mismatches.
 *
 * Useful for layout decisions that can't be expressed in Tailwind alone -
 * e.g. "render an overflow dropdown when the viewport is below `lg`":
 *
 * ```ts
 * const isNarrow = useMediaQuery("(max-width: 1023px)");
 * ```
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = React.useState<boolean>(false);

  React.useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mql = window.matchMedia(query);
    const update = () => setMatches(mql.matches);
    update();
    // addEventListener is the modern API; addListener is the Safari < 14 fallback.
    if (typeof mql.addEventListener === "function") {
      mql.addEventListener("change", update);
      return () => mql.removeEventListener("change", update);
    }
    mql.addListener(update);
    return () => mql.removeListener(update);
  }, [query]);

  return matches;
}
