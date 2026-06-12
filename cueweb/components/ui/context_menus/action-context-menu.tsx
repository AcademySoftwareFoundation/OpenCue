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
  copyFrameLogPath,
  copyFrameNameGivenRow,
  copyJobNameGivenRow,
  copyLayerNameGivenRow,
  createSubscriptionGivenRow,
  dependencyWizardGivenRow,
  dropExternalDependsGivenRow,
  dropInternalDependsGivenRow,
  eatFrameGivenRow,
  eatJobsDeadFramesGivenRow,
  eatLayerFramesGivenRow,
  editHostTagsGivenRow,
  editLayerPropertiesGivenRow,
  emailArtistGivenRow,
  killFrameGivenRow,
  killJobGivenRow,
  killLayerGivenRow,
  lockHostGivenRow,
  pauseJobGivenRow,
  rebootHostGivenRow,
  rebootHostWhenIdleGivenRow,
  requestCoresGivenRow,
  retryFrameGivenRow,
  retryJobsDeadFramesGivenRow,
  retryLayerDeadFramesGivenRow,
  retryLayerFramesGivenRow,
  setCoresGivenRow,
  setMaxRetriesGivenRow,
  setPriorityGivenRow,
  showPropertiesGivenRow,
  subscribeToJobGivenRow,
  unbookGivenRow,
  unlockHostGivenRow,
  unmonitorJobGivenRow,
  unpauseJobGivenRow,
  viewDependenciesGivenRow,
} from "@/app/utils/action_utils";
import { Frame } from "@/app/frames/frame-columns";
import { getFrameLogDir } from "@/app/utils/get_utils";
import { toastWarning } from "@/app/utils/notify_utils";
import { useDisableJobInteraction } from "@/app/utils/use_disable_job_interaction";
import { Row } from "@tanstack/react-table";
import { usePathname, useRouter } from "next/navigation";
import * as React from "react";
import { MdOutlineCancel } from "react-icons/md";
import {
  TbCopy,
  TbDots,
  TbExternalLink,
  TbEyeOff,
  TbHelp,
  TbLayoutDashboard,
  TbLink,
  TbLock,
  TbLockOpen,
  TbMessage,
  TbPacman,
  TbPlayerPause,
  TbPlayerPlay,
  TbPlugConnectedX,
  TbPlus,
  TbPower,
  TbRefresh,
  TbReload,
  TbSettings,
  TbStar,
  TbTag,
} from "react-icons/tb";
import { BaseContextMenu } from "./base-context-menu";
import { ContextMenuState, MenuItem } from "./useContextMenu";

// Helper for menu items that are not yet wired to a Cuebot backend.
// Surfaces a toast so users know the gap (and we get a single grep target
// when implementing them in Round 2).
const notYetImplemented = (label: string) => () => {
  toastWarning(`"${label}" is not yet implemented in CueWeb. Use CueGUI for now.`);
};

// Web-native equivalent of cuegui.Utils.popupView's $EDITOR launcher.
// The template comes from the build-time env var NEXT_PUBLIC_LOG_EDITOR_URL;
// `{path}` is replaced with the absolute log path. Examples:
//   vscode://file{path}
//   subl://open?url=file://{path}
// Empty (the default) hides the menu item entirely. Browser sandboxing
// rules out subprocess.Popen and reading $EDITOR directly, so the
// custom URL scheme is the closest analog.
const LOG_EDITOR_URL_TEMPLATE = (process.env.NEXT_PUBLIC_LOG_EDITOR_URL ?? "").trim();

// Derive a friendly menu label from the URL scheme so common editors
// get a sensible name automatically. Falls back to a generic phrasing
// when the scheme isn't recognized.
function logEditorMenuLabel(template: string): string {
  const lower = template.toLowerCase();
  if (lower.startsWith("vscode-insiders://")) return "View Log on VSCode Insiders";
  if (lower.startsWith("vscode://")) return "View Log on VSCode";
  if (lower.startsWith("subl://") || lower.startsWith("sublime://")) return "View Log on Sublime Text";
  if (lower.startsWith("txmt://")) return "View Log on TextMate";
  if (lower.startsWith("idea://")) return "View Log on IntelliJ";
  return "View Log in external editor";
}

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
  // Needed to build the absolute frame-log path for "Copy Log Path"
  // (`<job.logDir>/<job.name>.<frame.name>.rqlog`). Optional so the menu
  // still renders in contexts where the parent job isn't known yet, but
  // Copy Log Path will surface a toast warning in that case.
  job?: Job;
  contextMenuState: ContextMenuState;
  contextMenuHandleClose: () => void;
  contextMenuRef: React.RefObject<HTMLDivElement>;
  contextMenuTargetAreaRef: React.RefObject<HTMLDivElement>;
}

interface HostContextMenuProps {
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
  const router = useRouter();
  // "View Job" loads the selected row into the Monitor Jobs (Cuetopia) table.
  // It is meaningless on Cuetopia itself, so we only expose it on Monitor Cue.
  const pathname = usePathname();
  const isOnMonitorCue = pathname === "/monitor-cue";

  // Navigate to the tabbed job detail page at /jobs/<jobName>?tab=overview.
  // The page (app/jobs/[job-name]/page.tsx) owns the Overview / Layers /
  // Frames / Comments / Dependencies tabs and keeps the active tab in
  // sync with the URL, so this entry is a simple deep link.
  function handleViewJobDetails(row: Row<any>) {
    const job = row.original as Job;
    router.push(`/jobs/${encodeURIComponent(job.name)}?tab=overview`);
  }

  // "View Job" deep-links to the Cuetopia Monitor Jobs page (/) with the
  // selected job's name in the search query. The jobs table reads `search`
  // on mount, auto-loads the matching job into the monitored set, then
  // strips the param so a refresh doesn't re-fire. Same mechanism as the
  // "View in Monitor Jobs" button on the tabbed job detail page.
  function handleViewJob(row: Row<any>) {
    const job = row.original as Job;
    router.push(`/?search=${encodeURIComponent(job.name)}`);
  }

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
    const params = new URLSearchParams({ jobId: job.id });
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

  // Pause/Unpause is a single toggle (CueGUI parity): show "Unpause" when
  // the job is paused, "Pause" otherwise. destructiveActive already
  // disables the entry on FINISHED jobs and when the global safety flag
  // is set, so In Progress / Failing / Dependency all behave correctly.
  const isJobPaused = !!contextMenuState.row?.original.isPaused;

  // CueGUI parity: order + grouping mirror cuegui.MenuActions.JobActions
  const menuItems: MenuItem[] = [
    // -- Top group: identity + lookup actions ----------------------
    {
      label: "Unmonitor",
      onClick: handleUnmonitorJobGivenRow,
      isActive: true,
      component: <TbEyeOff className="mr-1" size={14} />,
    },
    // "View Job" loads the row into Cuetopia's Monitor Jobs table; on
    // Cuetopia itself the user is already viewing it, so the entry is
    // only included when the menu opens on the Monitor Cue page.
    ...(isOnMonitorCue
      ? ([
          {
            label: "View Job",
            onClick: handleViewJob,
            isActive: true,
            component: <TbDots className="mr-1" size={14} />,
          },
        ] as MenuItem[])
      : []),
    {
      // Tabbed detail page (Overview / Layers / Frames / Comments /
      // Dependencies) with URL-synced active-tab state. Lives at
      // /jobs/<jobName>?tab=<key> so the page is bookmarkable and
      // back-button-friendly.
      label: "View Job Details",
      onClick: handleViewJobDetails,
      isActive: true,
      component: <TbLayoutDashboard className="mr-1" size={14} />,
    },
    {
      label: "Copy Job Name",
      onClick: copyJobNameGivenRow,
      isActive: true,
      component: <TbCopy className="mr-1" size={14} />,
    },
    {
      label: "Email Artist...",
      onClick: emailArtistGivenRow,
      isActive: true,
      component: <TbMessage className="mr-1" size={14} />,
    },
    {
      label: "Request Cores...",
      onClick: requestCoresGivenRow,
      isActive: editable,
      component: <TbSettings className="mr-1" size={14} color={grayIfDisabled(editable)} />,
    },
    {
      // Opens a small dialog mirroring CueGUI's SubscribeToJobDialog. On
      // Save the address is registered with Cuebot via the AddSubscriber
      // RPC; Cuebot emails the subscriber when the job finishes.
      label: "Subscribe to Job",
      onClick: subscribeToJobGivenRow,
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
      onClick: viewDependenciesGivenRow,
      isActive: true,
      component: <TbLink className="mr-1" size={14} />,
    },
    {
      label: "Dependency Wizard...",
      onClick: dependencyWizardGivenRow,
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
      label: "Set Priority...",
      onClick: setPriorityGivenRow,
      isActive: editable,
      component: <TbSettings className="mr-1" size={14} color={grayIfDisabled(editable)} />,
    },
    {
      label: "Set Min/Max Cores...",
      onClick: setCoresGivenRow,
      isActive: editable,
      component: <TbSettings className="mr-1" size={14} color={grayIfDisabled(editable)} />,
    },
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

    // -- Pause / Unpause (single toggle) --------------------------
    {
      label: isJobPaused ? "Unpause" : "Pause",
      onClick: isJobPaused ? unpauseJobGivenRow : pauseJobGivenRow,
      isActive: destructiveActive,
      component: isJobPaused ? (
        <TbPlayerPlay className="mr-1" size={14} color={grayIfDisabled(destructiveActive)} />
      ) : (
        <TbPlayerPause className="mr-1" size={14} color={grayIfDisabled(destructiveActive)} />
      ),
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
      label: "Unbook...",
      onClick: unbookGivenRow,
      isActive: destructiveActive,
      component: <TbPlugConnectedX className="mr-1" size={14} color={grayIfDisabled(destructiveActive)} />,
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
    { label: "Copy Layer Name", onClick: copyLayerNameGivenRow, isActive: true, component: <TbCopy className="mr-1" size={14} /> },

    // Dependencies submenu flattened.
    { label: "View Dependencies...", onClick: notYetImplemented("View Dependencies"), isActive: true, component: <TbLink className="mr-1" size={14} /> },
    { label: "Dependency Wizard...", onClick: notYetImplemented("Dependency Wizard"), isActive: active, component: <TbHelp className="mr-1" size={14} color={active ? undefined : "gray"} /> },
    { label: "Mark done", onClick: notYetImplemented("Mark done"), isActive: active, component: <TbReload className="mr-1" size={14} color={active ? undefined : "gray"} /> },

    sep("group-reorder"),

    { label: "Reorder Frames...", onClick: notYetImplemented("Reorder Frames"), isActive: active, component: <TbSettings className="mr-1" size={14} color={active ? undefined : "gray"} /> },
    { label: "Stagger Frames...", onClick: notYetImplemented("Stagger Frames"), isActive: active, component: <TbSettings className="mr-1" size={14} color={active ? undefined : "gray"} /> },

    sep("group-properties"),

    { label: "Properties...", onClick: editLayerPropertiesGivenRow, isActive: true, component: <TbSettings className="mr-1" size={14} /> },

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

// Context menu for the Monitor Hosts table. Currently exposes Lock /
// Unlock (D2); reboot, tag edit and the other CueCommander host actions
// land in sibling issues and slot in here as they're built.
export const HostContextMenu: React.FC<HostContextMenuProps> = ({
  contextMenuState,
  contextMenuHandleClose,
  contextMenuRef,
  contextMenuTargetAreaRef,
}) => {
  // lockState drives which entry is live: a host can be Locked only when
  // it is currently OPEN, and Unlocked only when it is plainly LOCKED.
  // NIMBY_LOCKED hosts cannot be unlocked via this RPC (the gateway
  // rejects it), so both entries are inactive for them.
  const lockState = contextMenuState.row?.original.lockState as string | undefined;
  const canLock = lockState === "OPEN";
  const canUnlock = lockState === "LOCKED";

  // Hardware state gates the reboot entries. An immediate reboot is
  // pointless while the host is already REBOOTING; scheduling a
  // reboot-when-idle is pointless once it is already REBOOTING or
  // REBOOT_WHEN_IDLE.
  const hardwareState = contextMenuState.row?.original.state as string | undefined;
  const canReboot = hardwareState !== "REBOOTING";
  const canRebootWhenIdle =
    hardwareState !== "REBOOTING" && hardwareState !== "REBOOT_WHEN_IDLE";

  const items: MenuItem[] = [
    {
      label: "Lock",
      onClick: lockHostGivenRow,
      isActive: canLock,
      component: <TbLock className="mr-1" size={14} color={canLock ? undefined : "gray"} />,
    },
    {
      label: "Unlock",
      onClick: unlockHostGivenRow,
      isActive: canUnlock,
      component: <TbLockOpen className="mr-1" size={14} color={canUnlock ? undefined : "gray"} />,
    },

    sep("group-reboot"),

    {
      label: "Reboot",
      onClick: rebootHostGivenRow,
      isActive: canReboot,
      component: <TbPower className="mr-1" size={14} color={canReboot ? "red" : "gray"} />,
    },
    {
      label: "Reboot When Idle",
      onClick: rebootHostWhenIdleGivenRow,
      isActive: canRebootWhenIdle,
      component: <TbRefresh className="mr-1" size={14} color={canRebootWhenIdle ? undefined : "gray"} />,
    },

    sep("group-tags"),

    {
      label: "Edit Tags...",
      onClick: editHostTagsGivenRow,
      isActive: true,
      component: <TbTag className="mr-1" size={14} />,
    },
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

interface ShowContextMenuProps {
  contextMenuState: ContextMenuState;
  contextMenuHandleClose: () => void;
  contextMenuRef: React.RefObject<HTMLDivElement>;
  contextMenuTargetAreaRef: React.RefObject<HTMLDivElement>;
}

// Context menu for the Shows table (CueGUI ShowsWidget parity): Show
// Properties and Create Subscription.
export const ShowContextMenu: React.FC<ShowContextMenuProps> = ({
  contextMenuState,
  contextMenuHandleClose,
  contextMenuRef,
  contextMenuTargetAreaRef,
}) => {
  const items: MenuItem[] = [
    {
      label: "Show Properties",
      onClick: showPropertiesGivenRow,
      isActive: true,
      component: <TbSettings className="mr-1" size={14} />,
    },
    sep("group-subscription"),
    {
      label: "Create Subscription...",
      onClick: createSubscriptionGivenRow,
      isActive: true,
      component: <TbPlus className="mr-1" size={14} />,
    },
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
  job,
  contextMenuState,
  contextMenuHandleClose,
  contextMenuRef,
  contextMenuTargetAreaRef,
}) => {
  const router = useRouter();

  function handleKillFrameGivenRow(row: Row<any>) {
    killFrameGivenRow(row, username);
  }

  // Bind the parent job into the copy handler since the absolute log
  // path is `<job.logDir>/<job.name>.<frame.name>.rqlog`. The helper
  // surfaces a toast when `job` is undefined, so users get feedback
  // either way.
  const handleCopyLogPath = (row: Row<any>) => copyFrameLogPath(job, row);

  // CueGUI-parity "View Log": opens the same log-viewer route the
  // row-level double-click handler uses (handleFrameRowDoubleClick in
  // simple-data-table.tsx). The URL shape MUST stay in sync with that
  // handler - if either changes, update both. Requires `job` because
  // the log filename is `<job.name>.<frame.name>.rqlog`.
  const handleViewLog = (row: Row<any>) => {
    if (!job) {
      toastWarning("Frame log unavailable (no parent job context)");
      return;
    }
    const frame = row.original as Frame;
    const params = new URLSearchParams({
      frameId: frame.id,
      frameLogDir: getFrameLogDir(job, frame),
      username,
    });
    router.push(`/frames/${encodeURIComponent(frame.name)}?${params.toString()}`);
  };

  // External-editor opener: substitutes `{path}` in the configured URL
  // template with the absolute rqlog path and hands the result to the
  // OS via window.location.href, which the OS routes to whichever app
  // registered the URL scheme (VSCode, Sublime, TextMate, etc.). The
  // menu item is only rendered when LOG_EDITOR_URL_TEMPLATE is set, so
  // the early-returns below are belt-and-braces for stray invocations.
  const handleViewLogInEditor = (row: Row<any>) => {
    if (!LOG_EDITOR_URL_TEMPLATE) return;
    if (!job) {
      toastWarning("Frame log unavailable (no parent job context)");
      return;
    }
    const frame = row.original as Frame;
    // RQD only writes the rqlog file when it actually starts running a
    // frame. For WAITING / DEPEND frames the file doesn't exist on
    // disk, so launching the external editor with that path makes the
    // editor pop its own "path does not exist" dialog. Short-circuit
    // here with a clearer toast instead. `startTime === 0` is the
    // canonical "has not been dispatched yet" signal Cuebot exposes.
    if (!frame.startTime) {
      toastWarning(
        `Frame "${frame.name}" hasn't started running yet; no log file exists yet`,
      );
      return;
    }
    const absolutePath = getFrameLogDir(job, frame);
    // Plain string replace - we deliberately don't URL-encode the path
    // because the most common scheme (vscode://file/abs/path) expects
    // raw filesystem syntax. Schemes that need encoding can build
    // `file://{path}` and add their own encoder upstream if needed.
    const url = LOG_EDITOR_URL_TEMPLATE.replace("{path}", absolutePath);

    // Best-effort detection of "no app registered for this URL scheme".
    // There is no Web API to ask the browser whether a custom URL
    // scheme has a handler (it would be a fingerprinting vector), but
    // when the OS hands control to an installed app the browser loses
    // focus, which we can observe via blur / visibilitychange. If the
    // page stays focused past a short timeout the scheme almost
    // certainly didn't resolve - that's when we surface the toast.
    const editorLabel = logEditorMenuLabel(LOG_EDITOR_URL_TEMPLATE);
    let handlerActivated = false;
    const markActivated = () => {
      handlerActivated = true;
    };
    window.addEventListener("blur", markActivated, { once: true });
    document.addEventListener("visibilitychange", markActivated, { once: true });

    // Assigning location.href triggers the OS handler. If the URL
    // scheme is registered, control passes to that app and the
    // browser blurs; otherwise the browser eventually shows its own
    // "can't open <scheme>" dialog OR (on iOS) silently does nothing.
    window.location.href = url;

    window.setTimeout(() => {
      window.removeEventListener("blur", markActivated);
      document.removeEventListener("visibilitychange", markActivated);
      if (handlerActivated) return;
      // Heuristic miss-fire is possible (e.g. user Alt-Tabs away just
      // as the timer fires), but the false-positive cost is one extra
      // toast vs. the silent / cryptic OS dialog for the common case.
      toastWarning(
        `Couldn't open the log in ${editorLabel.replace(/^View Log on /, "")}. ` +
        "Install the editor (or set NEXT_PUBLIC_LOG_EDITOR_URL to a scheme " +
        "you have installed) - or use View Log to open it in CueWeb instead.",
      );
    }, 1500);
  };

  const { disabled: jobInteractionDisabled } = useDisableJobInteraction();
  const active = !jobInteractionDisabled;

  // CueGUI parity: order + grouping mirror cuegui.MenuActions.FrameActions
  const items: MenuItem[] = [
    // Tail Log + View Log both open the same frame-log viewer that the
    // row's double-click handler opens. CueGUI distinguishes them
    // (tail follows the end of the file vs. opens the static log);
    // CueWeb has one viewer today, so both items navigate there and the
    // viewer is responsible for the follow-vs-static behavior.
    { label: "Tail Log", onClick: handleViewLog, isActive: true, component: <TbDots className="mr-1" size={14} /> },
    { label: "View Log", onClick: handleViewLog, isActive: true, component: <TbDots className="mr-1" size={14} /> },
    // External-editor item is only rendered when the deployment sets
    // NEXT_PUBLIC_LOG_EDITOR_URL. Leaves the row out entirely when
    // unconfigured so users without a URL handler don't see a menu
    // entry that would do nothing.
    ...(LOG_EDITOR_URL_TEMPLATE
      ? [{
          label: logEditorMenuLabel(LOG_EDITOR_URL_TEMPLATE),
          onClick: handleViewLogInEditor,
          isActive: true,
          component: <TbExternalLink className="mr-1" size={14} />,
        } as MenuItem]
      : []),
    { label: "Copy Log Path", onClick: handleCopyLogPath, isActive: true, component: <TbCopy className="mr-1" size={14} /> },
    { label: "Copy Frame Name", onClick: copyFrameNameGivenRow, isActive: true, component: <TbCopy className="mr-1" size={14} /> },
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
