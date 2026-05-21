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


import { Job } from "@/app/jobs/columns";
import {
  autoEatOffGivenRow,
  autoEatOnGivenRow,
  copyJobNameGivenRow,
  dropExternalDependsGivenRow,
  dropInternalDependsGivenRow,
  eatFrameGivenRow,
  eatJobsDeadFramesGivenRow,
  eatLayerFramesGivenRow,
  killFrameGivenRow,
  killJobGivenRow,
  killLayerGivenRow,
  pauseJobGivenRow,
  retryFrameGivenRow,
  retryJobsDeadFramesGivenRow,
  retryLayerDeadFramesGivenRow,
  retryLayerFramesGivenRow,
  setMaxRetriesGivenRow,
  unmonitorJobGivenRow,
  unpauseJobGivenRow,
} from "@/app/utils/action_utils";
import { toastWarning } from "@/app/utils/notify_utils";
import { useDisableJobInteraction } from "@/app/utils/use_disable_job_interaction";
import { Row } from "@tanstack/react-table";
import * as React from "react";
import { MdOutlineCancel } from "react-icons/md";
import {
  TbCopy,
  TbDots,
  TbEyeOff,
  TbHelp,
  TbLink,
  TbMessage,
  TbPacman,
  TbPlayerPause,
  TbPlayerPlay,
  TbPlugConnectedX,
  TbReload,
  TbSettings,
  TbStar,
} from "react-icons/tb";
import { BaseContextMenu } from "./base-context-menu";
import { ContextMenuState, MenuItem } from "./useContextMenu";

// Helper for menu items that are not yet wired to a Cuebot backend.
// Surfaces a toast so users know the gap (and we get a single grep target
// when implementing them in Round 2).
const notYetImplemented = (label: string) => () => {
  toastWarning(`"${label}" is not yet implemented in CueWeb. Use CueGUI for now.`);
};

// Convenience for visual group dividers (CueGUI parity). Satisfies the
// MenuItem interface; BaseContextMenu renders an <hr> when separator is
// true and ignores the other fields.
const sep = (key: string): MenuItem => ({
  label: key,
  isActive: false,
  separator: true,
  onClick: () => {},
});

interface JobContextMenuProps {
  username: string;
  contextMenuState: ContextMenuState;
  contextMenuHandleClose: () => void;
  contextMenuRef: React.RefObject<HTMLDivElement>;
  contextMenuTargetAreaRef: React.RefObject<HTMLDivElement>;
  tableData: Job[];
  tableDataUnfiltered: Job[];
  rowSelection: { [key: number]: boolean };
  setTableData: React.Dispatch<React.SetStateAction<Job[]>>;
  setTableDataUnfiltered: React.Dispatch<React.SetStateAction<Job[]>>;
  setRowSelection: React.Dispatch<React.SetStateAction<{ [key: number]: boolean }>>;
  tableStorageName: string;
  unfilteredTableStorageName: string;
}

interface LayerContextMenuProps {
  username: string;
  contextMenuState: ContextMenuState;
  contextMenuHandleClose: () => void;
  contextMenuRef: React.RefObject<HTMLDivElement>;
  contextMenuTargetAreaRef: React.RefObject<HTMLDivElement>;
}

interface FrameContextMenuProps {
  username: string;
  contextMenuState: ContextMenuState;
  contextMenuHandleClose: () => void;
  contextMenuRef: React.RefObject<HTMLDivElement>;
  contextMenuTargetAreaRef: React.RefObject<HTMLDivElement>;
}

// Context menu for tables that contain jobs
export const JobContextMenu: React.FC<JobContextMenuProps> = ({
  username,
  contextMenuState,
  contextMenuHandleClose,
  contextMenuRef,
  contextMenuTargetAreaRef,
  tableData,
  tableDataUnfiltered,
  rowSelection,
  setTableData,
  setTableDataUnfiltered,
  setRowSelection,
  tableStorageName,
  unfilteredTableStorageName,
}) => {
  function handleUnmonitorJobGivenRow(row: Row<any>) {
    unmonitorJobGivenRow(
      row,
      tableData,
      tableDataUnfiltered,
      rowSelection,
      setTableData,
      setTableDataUnfiltered,
      setRowSelection,
      tableStorageName,
      unfilteredTableStorageName
    );
  }

  function handleKillJobGivenRow(row: Row<any>) {
    killJobGivenRow(row, username);
  }

  function handleCommentsGivenRow(row: Row<any>) {
    const job = row.original as Job;
    const params = new URLSearchParams({ jobId: job.id, username });
    const url = `/jobs/${encodeURIComponent(job.name)}/comments?${params.toString()}`;
    window.open(url, "_blank", "noopener,noreferrer");
  }

  const { disabled: jobInteractionDisabled } = useDisableJobInteraction();

  // If the row is null or the job's state is finished, set active as false
  const isActive = contextMenuState.row ? contextMenuState.row.original.state !== "FINISHED" : false;
  // Destructive items respect the per-row state AND the global safety flag.
  const destructiveActive = isActive && !jobInteractionDisabled;
  // Editable items (set priority, set retries, auto-eat, drop depends)
  // gate on the safety flag too but allow finished jobs to be edited the
  // way CueGUI does.
  const editable = !jobInteractionDisabled;
  const grayIfDisabled = (active: boolean) => (active ? undefined : "gray");

  // CueGUI parity: order + grouping mirror cuegui.MenuActions.JobActions
  const menuItems: MenuItem[] = [
    // -- Top group: identity + lookup actions ----------------------
    {
      label: "Unmonitor",
      onClick: handleUnmonitorJobGivenRow,
      isActive: true,
      component: <TbEyeOff className="mr-1" size={14} />,
    },
    {
      label: "View Job",
      onClick: notYetImplemented("View Job"),
      isActive: true,
      component: <TbDots className="mr-1" size={14} />,
    },
    {
      label: "Copy Job Name",
      onClick: copyJobNameGivenRow,
      isActive: true,
      component: <TbCopy className="mr-1" size={14} />,
    },
    {
      label: "Email Artist...",
      onClick: notYetImplemented("Email Artist"),
      isActive: true,
      component: <TbMessage className="mr-1" size={14} />,
    },
    {
      label: "Request Cores...",
      onClick: notYetImplemented("Request Cores"),
      isActive: editable,
      component: <TbSettings className="mr-1" size={14} color={grayIfDisabled(editable)} />,
    },
    {
      label: "Subscribe to Job",
      onClick: notYetImplemented("Subscribe to Job"),
      isActive: true,
      component: <TbStar className="mr-1" size={14} />,
    },
    {
      label: "Comments...",
      onClick: handleCommentsGivenRow,
      isActive: true,
      component: <TbMessage className="mr-1" size={14} />,
    },
    {
      label: "Use Local Cores...",
      onClick: notYetImplemented("Use Local Cores"),
      isActive: editable,
      component: <TbSettings className="mr-1" size={14} color={grayIfDisabled(editable)} />,
    },

    // Dependencies submenu flattened inline (CueGUI shows it as a
    // submenu; CueWeb has no submenu primitive yet, so it sits as a
    // contiguous group with the rest of the top section).
    {
      label: "View Dependencies...",
      onClick: notYetImplemented("View Dependencies"),
      isActive: true,
      component: <TbLink className="mr-1" size={14} />,
    },
    {
      label: "Dependency Wizard...",
      onClick: notYetImplemented("Dependency Wizard"),
      isActive: editable,
      component: <TbHelp className="mr-1" size={14} color={grayIfDisabled(editable)} />,
    },
    {
      label: "Drop External Dependencies",
      onClick: dropExternalDependsGivenRow,
      isActive: editable,
      component: <TbPlugConnectedX className="mr-1" size={14} color={grayIfDisabled(editable)} />,
    },
    {
      label: "Drop Internal Dependencies",
      onClick: dropInternalDependsGivenRow,
      isActive: editable,
      component: <TbPlugConnectedX className="mr-1" size={14} color={grayIfDisabled(editable)} />,
    },

    // Set user color submenu flattened to two stub entries; the full
    // 15-color picker lands when the back-end is wired.
    {
      label: "Set User Color...",
      onClick: notYetImplemented("Set User Color"),
      isActive: true,
      component: <TbStar className="mr-1" size={14} />,
    },
    {
      label: "Clear User Color",
      onClick: notYetImplemented("Clear User Color"),
      isActive: true,
      component: <TbStar className="mr-1" size={14} />,
    },

    sep("group-frame-controls"),

    // -- Frame-level controls (CueGUI parity).
    {
      label: "Set Max Retries...",
      onClick: setMaxRetriesGivenRow,
      isActive: editable,
      component: <TbSettings className="mr-1" size={14} color={grayIfDisabled(editable)} />,
    },
    {
      label: "Reorder Frames...",
      onClick: notYetImplemented("Reorder Frames"),
      isActive: editable,
      component: <TbSettings className="mr-1" size={14} color={grayIfDisabled(editable)} />,
    },
    {
      label: "Stagger Frames...",
      onClick: notYetImplemented("Stagger Frames"),
      isActive: editable,
      component: <TbSettings className="mr-1" size={14} color={grayIfDisabled(editable)} />,
    },

    sep("group-pause"),

    // -- Pause / Unpause ------------------------------------------
    {
      label: "Pause",
      onClick: pauseJobGivenRow,
      isActive: destructiveActive,
      component: <TbPlayerPause className="mr-1" size={14} color={grayIfDisabled(destructiveActive)} />,
    },
    {
      label: "Unpause",
      onClick: unpauseJobGivenRow,
      isActive: destructiveActive,
      component: <TbPlayerPlay className="mr-1" size={14} color={grayIfDisabled(destructiveActive)} />,
    },

    sep("group-eat-kill"),

    // -- Eat / Retry / Kill ---------------------------------------
    {
      label: "Auto-Eat On",
      onClick: autoEatOnGivenRow,
      isActive: editable,
      component: <TbPacman className="mr-1" size={14} color={grayIfDisabled(editable)} />,
    },
    {
      label: "Auto-Eat Off",
      onClick: autoEatOffGivenRow,
      isActive: editable,
      component: <TbPacman className="mr-1" size={14} color={grayIfDisabled(editable)} />,
    },
    {
      label: "Retry Dead Frames",
      onClick: retryJobsDeadFramesGivenRow,
      isActive: destructiveActive,
      component: <TbReload className="mr-1" size={14} color={grayIfDisabled(destructiveActive)} />,
    },
    {
      label: "Eat Dead Frames",
      onClick: eatJobsDeadFramesGivenRow,
      isActive: destructiveActive,
      component: <TbPacman className="mr-1" size={14} color={grayIfDisabled(destructiveActive)} />,
    },
    {
      label: "Unbook",
      onClick: notYetImplemented("Unbook"),
      isActive: editable,
      component: <TbSettings className="mr-1" size={14} color={grayIfDisabled(editable)} />,
    },
    {
      label: "Kill",
      onClick: handleKillJobGivenRow,
      isActive: destructiveActive,
      component: <MdOutlineCancel className="mr-1" size={14} color={grayIfDisabled(destructiveActive)} />,
    },

    sep("group-progress-bar"),

    // CueGUI parity: bottom of the menu. Toggles whether
    // the per-row progress bar is shown; CueWeb's Progress column is
    // controlled via the Columns dropdown for now, so this routes
    // through the standard "not yet implemented" toast until the
    // toggle is wired. On CueGUI, this option opens the CueProgBar tool
    {
      label: "Show Progress Bar",
      onClick: notYetImplemented("Show Progress Bar"),
      isActive: true,
      component: <TbSettings className="mr-1" size={14} />,
    },
  ];

  return (
    <BaseContextMenu
      items={menuItems}
      contextMenuState={contextMenuState}
      contextMenuHandleClose={contextMenuHandleClose}
      contextMenuRef={contextMenuRef}
      contextMenuTargetAreaRef={contextMenuTargetAreaRef}
    />
  );
};

// Context menu for tables that contain Layers
export const LayerContextMenu: React.FC<LayerContextMenuProps> = ({
  username,
  contextMenuState,
  contextMenuHandleClose,
  contextMenuRef,
  contextMenuTargetAreaRef,
}) => {
  function handleKillLayerGivenRow(row: Row<any>) {
    killLayerGivenRow(row, username);
  }

  const { disabled: jobInteractionDisabled } = useDisableJobInteraction();
  const active = !jobInteractionDisabled;

  // CueGUI parity: order + grouping mirror cuegui.MenuActions.LayerActions
  const items: MenuItem[] = [
    { label: "View Layer", onClick: notYetImplemented("View Layer"), isActive: true, component: <TbDots className="mr-1" size={14} /> },
    { label: "Copy Layer Name", onClick: notYetImplemented("Copy Layer Name"), isActive: true, component: <TbCopy className="mr-1" size={14} /> },

    // Dependencies submenu flattened.
    { label: "View Dependencies...", onClick: notYetImplemented("View Dependencies"), isActive: true, component: <TbLink className="mr-1" size={14} /> },
    { label: "Dependency Wizard...", onClick: notYetImplemented("Dependency Wizard"), isActive: active, component: <TbHelp className="mr-1" size={14} color={active ? undefined : "gray"} /> },
    { label: "Mark done", onClick: notYetImplemented("Mark done"), isActive: active, component: <TbReload className="mr-1" size={14} color={active ? undefined : "gray"} /> },

    sep("group-reorder"),

    { label: "Reorder Frames...", onClick: notYetImplemented("Reorder Frames"), isActive: active, component: <TbSettings className="mr-1" size={14} color={active ? undefined : "gray"} /> },
    { label: "Stagger Frames...", onClick: notYetImplemented("Stagger Frames"), isActive: active, component: <TbSettings className="mr-1" size={14} color={active ? undefined : "gray"} /> },

    sep("group-properties"),

    { label: "Properties...", onClick: notYetImplemented("Properties"), isActive: true, component: <TbSettings className="mr-1" size={14} /> },

    sep("group-actions"),

    { label: "Kill", onClick: handleKillLayerGivenRow, isActive: active, component: <MdOutlineCancel className="mr-1" size={14} color={active ? "red" : "gray"} /> },
    { label: "Eat", onClick: eatLayerFramesGivenRow, isActive: active, component: <TbPacman className="mr-1" size={14} color={active ? "orange" : "gray"} /> },
    { label: "Retry", onClick: retryLayerFramesGivenRow, isActive: active, component: <TbReload className="mr-1" size={14} color={active ? "black" : "gray"} /> },
    { label: "Retry Dead Frames", onClick: retryLayerDeadFramesGivenRow, isActive: active, component: <TbReload className="mr-1" size={14} color={active ? "red" : "gray"} /> },
  ];

  return (
    <BaseContextMenu
      items={items}
      contextMenuState={contextMenuState}
      contextMenuHandleClose={contextMenuHandleClose}
      contextMenuRef={contextMenuRef}
      contextMenuTargetAreaRef={contextMenuTargetAreaRef}
    />
  );
};

// Context menu for tables that contain Frames
export const FrameContextMenu: React.FC<FrameContextMenuProps> = ({
  username,
  contextMenuState,
  contextMenuHandleClose,
  contextMenuRef,
  contextMenuTargetAreaRef,
}) => {
  function handleKillFrameGivenRow(row: Row<any>) {
    killFrameGivenRow(row, username);
  }

  const { disabled: jobInteractionDisabled } = useDisableJobInteraction();
  const active = !jobInteractionDisabled;

  // CueGUI parity: order + grouping mirror cuegui.MenuActions.FrameActions
  const items: MenuItem[] = [
    { label: "Tail Log", onClick: notYetImplemented("Tail Log"), isActive: true, component: <TbDots className="mr-1" size={14} /> },
    { label: "View Log", onClick: notYetImplemented("View Log"), isActive: true, component: <TbDots className="mr-1" size={14} /> },
    { label: "Copy Log Path", onClick: notYetImplemented("Copy Log Path"), isActive: true, component: <TbCopy className="mr-1" size={14} /> },
    { label: "Copy Frame Name", onClick: notYetImplemented("Copy Frame Name"), isActive: true, component: <TbCopy className="mr-1" size={14} /> },
    { label: "View Host", onClick: notYetImplemented("View Host"), isActive: true, component: <TbDots className="mr-1" size={14} /> },

    // Dependencies submenu flattened (see Job menu note above).
    { label: "View Dependencies...", onClick: notYetImplemented("View Dependencies"), isActive: true, component: <TbLink className="mr-1" size={14} /> },
    { label: "Dependency Wizard...", onClick: notYetImplemented("Dependency Wizard"), isActive: active, component: <TbHelp className="mr-1" size={14} color={active ? undefined : "gray"} /> },
    { label: "Drop depends", onClick: notYetImplemented("Drop depends"), isActive: active, component: <TbPlugConnectedX className="mr-1" size={14} color={active ? undefined : "gray"} /> },
    { label: "Mark as waiting", onClick: notYetImplemented("Mark as waiting"), isActive: active, component: <TbReload className="mr-1" size={14} color={active ? undefined : "gray"} /> },
    { label: "Mark done", onClick: notYetImplemented("Mark done"), isActive: active, component: <TbReload className="mr-1" size={14} color={active ? undefined : "gray"} /> },

    sep("group-filter"),

    { label: "Filter Selected Layers", onClick: notYetImplemented("Filter Selected Layers"), isActive: true, component: <TbSettings className="mr-1" size={14} /> },
    { label: "Reorder...", onClick: notYetImplemented("Reorder"), isActive: active, component: <TbSettings className="mr-1" size={14} color={active ? undefined : "gray"} /> },

    sep("group-preview"),

    { label: "Preview All", onClick: notYetImplemented("Preview All"), isActive: true, component: <TbDots className="mr-1" size={14} /> },

    sep("group-actions"),

    { label: "Retry", onClick: retryFrameGivenRow, isActive: active, component: <TbReload className="mr-1" size={14} color={active ? "black" : "gray"} /> },
    { label: "Eat", onClick: eatFrameGivenRow, isActive: active, component: <TbPacman className="mr-1" size={14} color={active ? "orange" : "gray"} /> },
    { label: "Kill", onClick: handleKillFrameGivenRow, isActive: active, component: <MdOutlineCancel className="mr-1" size={14} color={active ? "red" : "gray"} /> },
    { label: "Eat and Mark done", onClick: notYetImplemented("Eat and Mark done"), isActive: active, component: <TbPacman className="mr-1" size={14} color={active ? "orange" : "gray"} /> },
    { label: "View Processes", onClick: notYetImplemented("View Processes"), isActive: true, component: <TbDots className="mr-1" size={14} /> },
  ];

  return (
    <BaseContextMenu
      items={items}
      contextMenuState={contextMenuState}
      contextMenuHandleClose={contextMenuHandleClose}
      contextMenuRef={contextMenuRef}
      contextMenuTargetAreaRef={contextMenuTargetAreaRef}
    />
  );
};
