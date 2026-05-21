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

import { useCallback, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Group, getShowGroups } from "@/app/utils/get_utils";
import { buildTreeFromGroups } from "./build-tree";
import {
  parseExpandedParam,
  serializeExpandedParam,
} from "./expanded-param";
import { GroupNode } from "./group-node";

const EXPANDED_PARAM = "expanded";

export function GroupTree({ showId }: { showId: string }) {
  const [groups, setGroups] = useState<Group[] | null>(null);

  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const expanded = useMemo(
    () => parseExpandedParam(searchParams.get(EXPANDED_PARAM)),
    [searchParams]
  );

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

      const params = new URLSearchParams(searchParams.toString());
      const serialized = serializeExpandedParam(next);
      if (serialized) params.set(EXPANDED_PARAM, serialized);
      else params.delete(EXPANDED_PARAM);

      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [expanded, pathname, router, searchParams]
  );

  if (groups === null) {
    return <p className="text-sm text-muted-foreground py-4">Loading group tree…</p>;
  }

  const tree = buildTreeFromGroups(groups);
  if (!tree) {
    return <p className="text-sm text-muted-foreground py-4">No groups in this show.</p>;
  }

  return (
    <div className="text-sm border rounded-md overflow-hidden">
      <GroupNode
        node={tree}
        depth={0}
        expanded={expanded}
        onToggle={onToggle}
      />
    </div>
  );
}
