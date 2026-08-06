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

import type { Show } from "@/app/utils/get_utils";
import { toastWarning } from "@/app/utils/notify_utils";
import { OPEN_SHOW_PROPERTIES_EVENT } from "@/components/ui/show-action-events";
import { OPEN_GROUP_PROPERTIES_EVENT } from "@/components/ui/group-properties-dialog";
import { OPEN_CREATE_GROUP_EVENT } from "@/components/ui/create-group-dialog";
import { OPEN_VIEW_FILTERS_EVENT } from "@/components/ui/view-filters-dialog";
import { OPEN_TASK_PROPERTIES_EVENT } from "@/components/ui/task-properties-dialog";
import { OPEN_SERVICE_PROPERTIES_EVENT } from "@/components/ui/service-properties-dialog";

/**
 * Right-click menu on a Monitor Cue show row (CueGUI CueCommander Monitor Cue
 * RootGroup menu parity). Rendered as a fixed positioned menu and dismissed on
 * any outside interaction. Each item dispatches a CustomEvent that the matching
 * page-level dialog listens for, mirroring the rest of CueWeb's menu wiring.
 */

export type ShowMenuState = { x: number; y: number; show: Show };

export function MonitorCueShowMenu({
  menu,
  onClose,
}: {
  menu: ShowMenuState | null;
  onClose: () => void;
}) {
  React.useEffect(() => {
    if (!menu) return;
    const close = () => onClose();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("click", close);
    window.addEventListener("scroll", close, true);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("keydown", onKey);
    };
  }, [menu, onClose]);

  if (!menu) return null;

  function dispatch(name: string, detail: object) {
    window.dispatchEvent(new CustomEvent(name, { detail }));
    onClose();
  }

  // CueGUI menu items not yet ported. Surface a toast so the menu has full
  // parity while the dialogs are still pending.
  function notImplemented(label: string) {
    toastWarning(`${label} is not implemented yet.`);
    onClose();
  }

  const item = (label: string, onClick: () => void) => (
    <button
      type="button"
      className="block w-full rounded px-2 py-1.5 text-left hover:bg-accent"
      onClick={onClick}
    >
      {label}
    </button>
  );

  return (
    <div
      className="fixed z-50 min-w-56 rounded-md border bg-popover p-1 text-sm text-popover-foreground shadow-md"
      style={{ left: menu.x, top: menu.y }}
      onClick={(e) => e.stopPropagation()}
    >
      {item("Show Properties...", () => dispatch(OPEN_SHOW_PROPERTIES_EVENT, { show: menu.show }))}
      {item("Service Properties...", () => dispatch(OPEN_SERVICE_PROPERTIES_EVENT, { show: menu.show }))}
      {item("Group Properties...", () => dispatch(OPEN_GROUP_PROPERTIES_EVENT, { show: menu.show }))}
      {item("Task Properties...", () => dispatch(OPEN_TASK_PROPERTIES_EVENT, { show: menu.show }))}
      {item("View Filters...", () => dispatch(OPEN_VIEW_FILTERS_EVENT, { show: menu.show }))}
      {item("Create Group...", () => dispatch(OPEN_CREATE_GROUP_EVENT, { show: menu.show }))}
      <div className="my-1 h-px bg-border" />
      {item("Change Cuewho...", () => notImplemented("Change Cuewho"))}
      {item("View Cuewho", () => notImplemented("View Cuewho"))}
    </div>
  );
}
