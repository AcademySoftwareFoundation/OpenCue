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
  unmonitorJobGivenRow,
} from "@/app/utils/action_utils";
import { useDisableJobInteraction } from "@/app/utils/use_disable_job_interaction";
import { Row } from "@tanstack/react-table";
import * as React from "react";
import { MdOutlineCancel } from "react-icons/md";
import { TbEyeOff, TbMessage, TbPacman, TbPlayerPause, TbReload } from "react-icons/tb";
import { BaseContextMenu } from "./base-context-menu";
import { ContextMenuState, MenuItem } from "./useContextMenu";

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

  const menuItems: MenuItem[] = [
    { label: "Unmonitor", onClick: handleUnmonitorJobGivenRow, isActive: true, component: <TbEyeOff className="mr-1" size={13} color="black" /> },
    { label: "Comments", onClick: handleCommentsGivenRow, isActive: true, component: <TbMessage className="mr-1" size={14} color="black" /> },
    { label: "Pause", onClick: pauseJobGivenRow, isActive: destructiveActive, component: <TbPlayerPause className="mr-1" size={14} color={destructiveActive ? "blue" : "gray"} /> },
    { label: "Retry Dead Frames", onClick: retryJobsDeadFramesGivenRow, isActive: destructiveActive, component: <TbReload className="mr-1" size={14} color={destructiveActive ? "red" : "gray"} /> },
    { label: "Eat Dead Frames", onClick: eatJobsDeadFramesGivenRow, isActive: destructiveActive, component: <TbPacman className="mr-1" size={14} color={destructiveActive ? "orange" : "gray"} /> },
    { label: "Kill", onClick: handleKillJobGivenRow, isActive: destructiveActive, component: <MdOutlineCancel className="mr-1" size={14} color={destructiveActive ? "red" : "gray"} /> },
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

  const items: MenuItem[] = [
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

  const items: MenuItem[] = [
    { label: "Retry", onClick: retryFrameGivenRow, isActive: active, component: <TbReload className="mr-1" size={14} color={active ? "black" : "gray"} /> },
    { label: "Eat", onClick: eatFrameGivenRow, isActive: active, component: <TbPacman className="mr-1" size={14} color={active ? "orange" : "gray"} /> },
    { label: "Kill", onClick: handleKillFrameGivenRow, isActive: active, component: <MdOutlineCancel className="mr-1" size={14} color={active ? "red" : "gray"} /> },
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
