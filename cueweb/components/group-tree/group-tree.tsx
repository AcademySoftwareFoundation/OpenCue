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

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useTransition,
} from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  DragDropProvider,
  DragOverlay,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/react";
import { Group, getShowGroups, getGroupJobs } from "@/app/utils/get_utils";
import { reparentGroups, reparentJobs } from "@/app/utils/action_utils";
import { toastWarning } from "@/app/utils/notify_utils";
import { buildTreeFromGroups } from "./build-tree";
import {
  parseExpandedParam,
  serializeExpandedParam,
} from "./expanded-param";
import {
  applyGroupReparent,
  applyJobReparent,
  canReparentGroup,
  type JobsState,
} from "./dnd-helpers";
import { GroupNode } from "./group-node";
import { GroupTreeProvider } from "./group-tree-context";
import { DragPreview } from "./drag-preview";

const EXPANDED_PARAM = "expanded";

type ActiveDrag = { id: string; type: string; fromGroupId?: string };

export function GroupTree({ showId }: { showId: string }) {
  const [groups, setGroups] = useState<Group[] | null>(null);
  const [jobsByGroup, setJobsByGroup] = useState<JobsState>(new Map());
  const [activeDrag, setActiveDrag] = useState<ActiveDrag | null>(null);

  // Serialize reparents: one in flight at a time, so concurrent moves can't
  // race into a backend parentage cycle. Cleared when the persist refetch lands.
  const reparentingRef = useRef(false);

  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();

  // Local state drives rendering; the URL is a write-through mirror for deep links.
  const [expanded, setExpanded] = useState<Set<string>>(() =>
    parseExpandedParam(searchParams.get(EXPANDED_PARAM)),
  );

  // Last URL value we synced, so the URL→local effect skips its own writes.
  const lastSyncedUrlRef = useRef<string>(searchParams.get(EXPANDED_PARAM) ?? "");

  useEffect(() => {
    const current = searchParams.get(EXPANDED_PARAM) ?? "";
    if (current !== lastSyncedUrlRef.current) {
      lastSyncedUrlRef.current = current;
      setExpanded(parseExpandedParam(current));
    }
  }, [searchParams]);

  useEffect(() => {
    let cancelled = false;
    getShowGroups(showId).then(result => {
      if (!cancelled) setGroups(result);
    });
    return () => { cancelled = true; };
  }, [showId]);

  const onToggle = useCallback(
    (groupId: string, open: boolean) => {
      const next = new Set(expanded);
      if (open) next.add(groupId);
      else next.delete(groupId);

      setExpanded(next);

      // Mirror to the URL in a transition so it can't block the open animation.
      const serialized = serializeExpandedParam(next);
      lastSyncedUrlRef.current = serialized;
      const params = new URLSearchParams(searchParams.toString());
      if (serialized) params.set(EXPANDED_PARAM, serialized);
      else params.delete(EXPANDED_PARAM);
      const query = params.toString();
      startTransition(() => {
        router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
      });
    },
    [expanded, pathname, router, searchParams, startTransition],
  );

  // Each group's jobs are fetched at most once (not re-fetched on re-expand).
  const requestedJobsRef = useRef<Set<string>>(new Set());

  const requestJobsFor = useCallback((groupId: string) => {
    if (requestedJobsRef.current.has(groupId)) return;
    requestedJobsRef.current.add(groupId);

    setJobsByGroup(prev => {
      const next = new Map(prev);
      next.set(groupId, "loading");
      return next;
    });
    getGroupJobs(groupId)
      .then(result => {
        setJobsByGroup(prev => {
          const next = new Map(prev);
          next.set(groupId, result);
          return next;
        });
      })
      .catch(() => {
        // Clear the guard so a later expand can retry.
        requestedJobsRef.current.delete(groupId);
        setJobsByGroup(prev => {
          const next = new Map(prev);
          next.delete(groupId);
          return next;
        });
      });
  }, []);

  // Mirrors onDragEnd's rules so only genuinely droppable targets highlight.
  const isValidDropTarget = useCallback(
    (targetGroupId: string) => {
      if (!activeDrag || !groups) return false;
      if (activeDrag.type === "group") {
        return canReparentGroup(groups, activeDrag.id, targetGroupId);
      }
      if (activeDrag.type === "job") {
        return activeDrag.fromGroupId !== targetGroupId;
      }
      return false;
    },
    [activeDrag, groups],
  );

  // Detached persistence (see onDragEnd): roll back on error, refetch on success.
  const persistGroupReparent = useCallback(
    async (sourceId: string, targetId: string, before: Group[]) => {
      try {
        const ok = await reparentGroups(targetId, [sourceId]);
        if (!ok) {
          setGroups(before);
          return;
        }
        const fresh = await getShowGroups(showId);
        // Empty means the refetch failed (a show always has a root); keep optimistic state.
        if (fresh.length > 0) setGroups(fresh);
      } finally {
        reparentingRef.current = false;
      }
    },
    [showId],
  );

  const persistJobReparent = useCallback(
    async (sourceId: string, fromGroupId: string, targetId: string, before: JobsState) => {
      try {
        const ok = await reparentJobs(targetId, [sourceId]);
        if (!ok) {
          setJobsByGroup(before);
          return;
        }
        const fresh = await getShowGroups(showId);
        // Empty means the refetch failed (a show always has a root); keep optimistic state.
        if (fresh.length > 0) setGroups(fresh);
      } finally {
        reparentingRef.current = false;
      }
    },
    [showId],
  );

  const onDragStart = (event: DragStartEvent) => {
    const source = event.operation.source;
    if (!source) return;
    const data = source.data as { type?: string; fromGroupId?: string };
    if (data.type !== "group" && data.type !== "job") return;
    setActiveDrag({ id: String(source.id), type: data.type, fromGroupId: data.fromGroupId });
  };

  // Must stay synchronous: dnd-kit defers drag cleanup until this handler's
  // render commits, so awaiting the slow reparent here would stall the next
  // drag. Do the cheap checks now; defer the update + persistence to a macrotask.
  const onDragEnd = (event: DragEndEvent) => {
    setActiveDrag(null);
    if (event.canceled) return;
    const { source, target } = event.operation;
    if (!source || !target || !groups) return;

    const data = source.data as { type?: string; fromGroupId?: string };
    const sourceId = String(source.id);
    const targetId = String(target.id);

    if (reparentingRef.current) {
      toastWarning("A reparent is already in progress — please wait for it to finish.");
      return;
    }

    if (data.type === "group") {
      if (!canReparentGroup(groups, sourceId, targetId)) return;
      reparentingRef.current = true;
      const before = groups;
      setTimeout(() => {
        setGroups(applyGroupReparent(before, sourceId, targetId));
        void persistGroupReparent(sourceId, targetId, before);
      }, 0);
    } else if (data.type === "job") {
      const fromGroupId = data.fromGroupId;
      if (!fromGroupId || fromGroupId === targetId) return;
      reparentingRef.current = true;
      const before = jobsByGroup;
      setTimeout(() => {
        setJobsByGroup(applyJobReparent(before, sourceId, fromGroupId, targetId));
        void persistJobReparent(sourceId, fromGroupId, targetId, before);
      }, 0);
    }
  };

  const contextValue = useMemo(
    () => ({ expanded, onToggle, jobsByGroup, requestJobsFor, isValidDropTarget }),
    [expanded, onToggle, jobsByGroup, requestJobsFor, isValidDropTarget],
  );

  if (groups === null) {
    return <p className="text-sm text-muted-foreground py-4">Loading group tree…</p>;
  }

  const tree = buildTreeFromGroups(groups);
  if (!tree) {
    return <p className="text-sm text-muted-foreground py-4">No groups in this show.</p>;
  }

  return (
    <DragDropProvider onDragStart={onDragStart} onDragEnd={onDragEnd}>
      <GroupTreeProvider value={contextValue}>
        <div className="text-sm border rounded-md overflow-hidden">
          <GroupNode node={tree} depth={0} />
        </div>
      </GroupTreeProvider>
      <DragOverlay dropAnimation={null}>
        {(source) => {
          const data = source.data as { type?: string; name?: string };
          if (data.type !== "group" && data.type !== "job") return null;
          return <DragPreview type={data.type} name={data.name ?? ""} />;
        }}
      </DragOverlay>
    </DragDropProvider>
  );
}
