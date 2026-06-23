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

import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import * as React from "react";

import { HELP_ITEMS } from "@/app/utils/help_menu";
import { NAV_MENUS } from "@/app/utils/menus";
import {
  buildSplitUrl,
  DEFAULT_LEFT,
  DEFAULT_RIGHT,
} from "@/app/utils/split_view_utils";
import { useAttributesPanel } from "@/app/utils/use_attributes_panel";
import { useCuebotFacility } from "@/app/utils/use_cuebot_facility";
import { useDisableJobInteraction } from "@/app/utils/use_disable_job_interaction";
import { useImmersiveMode } from "@/app/utils/use_immersive_mode";
import { CUEWEB_OPEN_ABOUT_EVENT } from "@/components/ui/about-dialog";

/**
 * A flat, searchable list of every menu command in CueWeb - used by the
 * Help search box (CueGUI parity: searching the Help menu finds items
 * across every top-level menu, not just the Help entries themselves).
 */
export interface MenuCommand {
  /** Stable id for React keys. */
  id: string;
  /** Top-level menu the command belongs to ("File", "Cuetopia", ...). */
  group: string;
  /** Leaf label ("Monitor Jobs", "Disable Job Interaction", ...). */
  label: string;
  /** Optional short hint shown after the label (e.g. "open", "toggle"). */
  hint?: string;
  /** Invoked when the user selects this command. */
  run: () => void;
}

export function useMenuRegistry(): MenuCommand[] {
  const router = useRouter();
  const { data: session } = useSession();
  const isAdmin = (session as { isAdmin?: boolean } | null)?.isAdmin ?? true;
  const { toggle: toggleJobInteraction } = useDisableJobInteraction();
  const { facilities, setFacility } = useCuebotFacility();
  const { toggle: toggleAttributes } = useAttributesPanel();
  const { toggle: toggleImmersive } = useImmersiveMode();

  return React.useMemo<MenuCommand[]>(() => {
    const cmds: MenuCommand[] = [];

    // File
    cmds.push({
      id: "file.disable-job-interaction",
      group: "File",
      label: "Disable Job Interaction",
      hint: "toggle",
      run: toggleJobInteraction,
    });

    // Cuebot Facility
    for (const f of facilities) {
      cmds.push({
        id: `facility.${f}`,
        group: "Cuebot Facility",
        label: f,
        run: () => setFacility(f),
      });
    }

    // Cuetopia / CueCommander / Admin (route destinations). Admin-only menus
    // are excluded from the search palette for non-admins.
    for (const menu of NAV_MENUS) {
      if (menu.adminOnly && !isAdmin) continue;
      for (const item of menu.items) {
        cmds.push({
          id: `${menu.label.toLowerCase()}${item.href}`,
          group: menu.label,
          label: item.label,
          run: () => router.push(item.href),
        });
      }
    }

    // Other
    cmds.push({
      id: "other.attributes",
      group: "Other",
      label: "Attributes",
      hint: "toggle panel",
      run: toggleAttributes,
    });
    cmds.push({
      id: "other.immersive",
      group: "Other",
      label: "Immersive (full-screen)",
      hint: "toggle",
      run: toggleImmersive,
    });
    cmds.push({
      id: "other.split-view",
      group: "Other",
      label: "Split view",
      hint: "open",
      run: () => router.push(buildSplitUrl(DEFAULT_LEFT, DEFAULT_RIGHT)),
    });

    // Help (external links)
    for (const item of HELP_ITEMS) {
      cmds.push({
        id: `help.${item.label}`,
        group: "Help",
        label: item.label,
        hint: "external",
        run: () => {
          if (typeof window !== "undefined") {
            window.open(item.href, "_blank", "noopener,noreferrer");
          }
        },
      });
    }

    // Help -> About CueWeb (opens the About dialog, not an external link).
    cmds.push({
      id: "help.about",
      group: "Help",
      label: "About CueWeb",
      hint: "dialog",
      run: () => {
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent(CUEWEB_OPEN_ABOUT_EVENT));
        }
      },
    });

    return cmds;
  }, [router, isAdmin, toggleJobInteraction, facilities, setFacility, toggleAttributes, toggleImmersive]);
}

/**
 * Case-insensitive substring match against `group > label` (and label
 * alone). Returns the original ordering of matches; empty query returns
 * every command.
 */
export function filterMenuCommands(
  commands: MenuCommand[],
  query: string,
): MenuCommand[] {
  const q = query.trim().toLowerCase();
  if (!q) return commands;
  return commands.filter((c) => {
    const haystack = `${c.group} > ${c.label}`.toLowerCase();
    return haystack.includes(q) || c.label.toLowerCase().includes(q);
  });
}
