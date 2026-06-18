/**
 * @jest-environment jsdom
 */

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
import { act, renderHook } from "@testing-library/react";

import {
  readImmersiveFromStorage,
  STORAGE_KEY,
  useImmersiveMode,
} from "@/app/utils/use_immersive_mode";

describe("use_immersive_mode", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("readImmersiveFromStorage", () => {
    it("returns false when nothing is stored", () => {
      expect(readImmersiveFromStorage()).toBe(false);
    });

    it("returns true only for the JSON literal true", () => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(true));
      expect(readImmersiveFromStorage()).toBe(true);
    });

    it("returns false for a non-true stored value", () => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(false));
      expect(readImmersiveFromStorage()).toBe(false);
    });

    it("returns false for malformed JSON", () => {
      localStorage.setItem(STORAGE_KEY, "{not json");
      expect(readImmersiveFromStorage()).toBe(false);
    });
  });

  describe("useImmersiveMode", () => {
    it("starts false and hydrates from storage on mount", () => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(true));
      const { result } = renderHook(() => useImmersiveMode());
      // After mount, the effect reconciles from storage.
      expect(result.current.immersive).toBe(true);
    });

    it("setImmersive persists to localStorage and updates state", () => {
      const { result } = renderHook(() => useImmersiveMode());
      expect(result.current.immersive).toBe(false);

      act(() => result.current.setImmersive(true));

      expect(result.current.immersive).toBe(true);
      expect(localStorage.getItem(STORAGE_KEY)).toBe(JSON.stringify(true));
    });

    it("toggle flips the persisted value", () => {
      const { result } = renderHook(() => useImmersiveMode());

      act(() => result.current.toggle());
      expect(result.current.immersive).toBe(true);
      expect(readImmersiveFromStorage()).toBe(true);

      act(() => result.current.toggle());
      expect(result.current.immersive).toBe(false);
      expect(readImmersiveFromStorage()).toBe(false);
    });

    it("syncs across tabs via the storage event", () => {
      const { result } = renderHook(() => useImmersiveMode());
      expect(result.current.immersive).toBe(false);

      act(() => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(true));
        window.dispatchEvent(
          new StorageEvent("storage", {
            key: STORAGE_KEY,
            newValue: JSON.stringify(true),
          }),
        );
      });

      expect(result.current.immersive).toBe(true);
    });

    it("ignores storage events for unrelated keys", () => {
      const { result } = renderHook(() => useImmersiveMode());

      act(() => {
        window.dispatchEvent(
          new StorageEvent("storage", {
            key: "cueweb.some.other.key",
            newValue: JSON.stringify(true),
          }),
        );
      });

      expect(result.current.immersive).toBe(false);
    });

    it("keeps two hook instances in sync within the same tab", () => {
      const a = renderHook(() => useImmersiveMode());
      const b = renderHook(() => useImmersiveMode());

      act(() => a.result.current.setImmersive(true));

      // The CustomEvent dispatched by setImmersive updates the other instance.
      expect(a.result.current.immersive).toBe(true);
      expect(b.result.current.immersive).toBe(true);
    });
  });
});
