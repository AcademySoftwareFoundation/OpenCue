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
 * Attributes panel - CueGUI parity (Views/Plugins > Other > Attributes).
 * The panel is a docked drawer that can sit on the right, bottom, left or
 * top of the viewport. Its open state and dock position are persisted to
 * `localStorage` and synced across components via a CustomEvent + the
 * browser's built-in `storage` event.
 */

export type AttributesPanelPosition = "right" | "bottom" | "left" | "top";

const ALL_POSITIONS: AttributesPanelPosition[] = [
  "right",
  "bottom",
  "left",
  "top",
];

const OPEN_KEY = "cueweb.attributes.open";
const POSITION_KEY = "cueweb.attributes.position";
const CHANGE_EVENT = "cueweb:attributes-panel-changed";

function readOpen(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return JSON.parse(window.localStorage.getItem(OPEN_KEY) ?? "false") === true;
  } catch {
    return false;
  }
}

function readPosition(): AttributesPanelPosition {
  if (typeof window === "undefined") return "right";
  try {
    const raw = window.localStorage.getItem(POSITION_KEY);
    if (raw && ALL_POSITIONS.includes(raw as AttributesPanelPosition)) {
      return raw as AttributesPanelPosition;
    }
  } catch {
    // ignore
  }
  return "right";
}

function writeOpen(value: boolean): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(OPEN_KEY, JSON.stringify(value));
  } catch {
    // ignore
  }
}

function writePosition(value: AttributesPanelPosition): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(POSITION_KEY, value);
  } catch {
    // ignore
  }
}

function dispatchChange(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
}

export function useAttributesPanel(): {
  isOpen: boolean;
  position: AttributesPanelPosition;
  positions: AttributesPanelPosition[];
  setOpen: (open: boolean) => void;
  toggle: () => void;
  setPosition: (position: AttributesPanelPosition) => void;
} {
  // SSR-safe defaults match the first client render to avoid hydration
  // mismatches; reconcile from localStorage on mount.
  const [isOpen, setIsOpenState] = React.useState<boolean>(false);
  const [position, setPositionState] =
    React.useState<AttributesPanelPosition>("right");

  React.useEffect(() => {
    setIsOpenState(readOpen());
    setPositionState(readPosition());

    const handler = () => {
      setIsOpenState(readOpen());
      setPositionState(readPosition());
    };
    const storageHandler = (e: StorageEvent) => {
      if (e.key === OPEN_KEY || e.key === POSITION_KEY) handler();
    };

    window.addEventListener(CHANGE_EVENT, handler);
    window.addEventListener("storage", storageHandler);
    return () => {
      window.removeEventListener(CHANGE_EVENT, handler);
      window.removeEventListener("storage", storageHandler);
    };
  }, []);

  const setOpen = React.useCallback((open: boolean) => {
    writeOpen(open);
    setIsOpenState(open);
    dispatchChange();
  }, []);

  const toggle = React.useCallback(() => {
    const next = !readOpen();
    writeOpen(next);
    setIsOpenState(next);
    dispatchChange();
  }, []);

  const setPosition = React.useCallback(
    (next: AttributesPanelPosition) => {
      if (!ALL_POSITIONS.includes(next)) return;
      writePosition(next);
      setPositionState(next);
      dispatchChange();
    },
    [],
  );

  return {
    isOpen,
    position,
    positions: ALL_POSITIONS,
    setOpen,
    toggle,
    setPosition,
  };
}
