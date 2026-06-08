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

import { procColumns } from "@/app/hosts/[host-name]/proc-columns";
import { kbStringToHuman } from "@/app/hosts/host_format_utils";
import { UNKNOWN_USER } from "@/app/utils/constants";
import {
  Host,
  JobComment,
  Proc,
  findHostByName,
  getHostComments,
  getHostProcs,
} from "@/app/utils/get_utils";
import { handleError } from "@/app/utils/notify_utils";
import { Breadcrumbs } from "@/components/ui/breadcrumbs";
import { Button } from "@/components/ui/button";
import { EditHostTagsDialog } from "@/components/ui/edit-host-tags-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import {
  HOSTS_CHANGED_EVENT,
  OPEN_HOST_TAGS_EVENT,
  type HostsChangedDetail,
} from "@/components/ui/host-action-events";
import { SimpleDataTable } from "@/components/ui/simple-data-table";
import { Skeleton } from "@/components/ui/skeleton";
import { Status } from "@/components/ui/status";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Cpu, MessageSquare, Server, Tag } from "lucide-react";
import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";
import * as React from "react";

const PROCS_REFRESH_MS = 15000;

const TAB_KEYS = ["overview", "procs", "comments", "tags"] as const;
type TabKey = (typeof TAB_KEYS)[number];

const isTabKey = (value: string | null | undefined): value is TabKey =>
  !!value && (TAB_KEYS as readonly string[]).includes(value);

function formatTimestamp(unixSeconds: number | undefined): string {
  if (!unixSeconds) return "-";
  return new Date(unixSeconds * 1000).toLocaleString();
}

export default function HostDetailPage() {
  const params = useParams<{ "host-name": string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const hostName = decodeURIComponent(params?.["host-name"] ?? "");
  const tabParam = searchParams.get("tab");
  const tab: TabKey = isTabKey(tabParam) ? tabParam : "overview";

  const [host, setHost] = React.useState<Host | null>(null);
  const [hostLoading, setHostLoading] = React.useState(true);
  const [hostError, setHostError] = React.useState<string | null>(null);

  const [procs, setProcs] = React.useState<Proc[]>([]);
  const [procsLoading, setProcsLoading] = React.useState(false);
  const [comments, setComments] = React.useState<JobComment[]>([]);
  const [commentsLoading, setCommentsLoading] = React.useState(false);

  const [currentUser, setCurrentUser] = React.useState<string>(UNKNOWN_USER);

  React.useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/auth/session");
        if (res.ok) {
          const session = await res.json();
          if (session?.user?.email) {
            setCurrentUser(String(session.user.email).split("@")[0]);
          } else if (session?.user?.name) {
            setCurrentUser(String(session.user.name));
          }
        }
      } catch {
        // Leave as UNKNOWN_USER; only governs the frame-log viewer header.
      }
    })();
  }, []);

  const mountedRef = React.useRef(true);
  React.useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Resolve the host by its exact name (FindHost). `silent` skips the
  // loading skeleton for background reconciles (e.g. after a tag edit).
  const loadHost = React.useCallback(
    async (silent = false) => {
      if (!hostName) {
        setHost(null);
        setHostError("Host not found.");
        setHostLoading(false);
        return;
      }
      if (!silent) setHostLoading(true);
      setHostError(null);
      try {
        const fetched = await findHostByName(hostName);
        if (!mountedRef.current) return;
        if (!fetched) {
          setHost(null);
          setHostError("Host not found.");
        } else {
          setHost(fetched);
        }
      } catch (error) {
        if (!mountedRef.current) return;
        handleError(error, "Error loading host");
        setHostError("Error loading host.");
      } finally {
        if (mountedRef.current && !silent) setHostLoading(false);
      }
    },
    [hostName],
  );

  React.useEffect(() => {
    loadHost();
  }, [loadHost]);

  // Tag edits (and other host actions) fire cueweb:hosts-changed. Patch the
  // affected fields immediately so the Tags tab updates without a flash, then
  // silently reconcile with Cuebot in case it normalized the tag set.
  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<HostsChangedDetail>).detail;
      if (!detail?.hostIds?.length || !detail.patch) return;
      setHost((prev) =>
        prev && detail.hostIds.includes(prev.id) ? { ...prev, ...detail.patch } : prev,
      );
      loadHost(true);
    }
    window.addEventListener(HOSTS_CHANGED_EVENT, handler);
    return () => window.removeEventListener(HOSTS_CHANGED_EVENT, handler);
  }, [loadHost]);

  // Procs tab: fetch immediately on activation, then refresh every 15s while
  // it stays the active tab. Polls are serialized so a slow request can't be
  // overtaken by a newer tick.
  React.useEffect(() => {
    if (!host || tab !== "procs") return;
    let cancelled = false;
    let inFlight = false;
    let first = true;

    const run = async () => {
      if (inFlight) return;
      inFlight = true;
      if (first) setProcsLoading(true);
      try {
        const data = await getHostProcs(host);
        if (!cancelled) setProcs(data);
      } catch (error) {
        if (!cancelled) handleError(error, "Error loading procs");
      } finally {
        inFlight = false;
        if (!cancelled && first) {
          setProcsLoading(false);
          first = false;
        }
      }
    };

    run();
    const interval = setInterval(run, PROCS_REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [host, tab]);

  // Comments tab: fetch once on activation (comments change rarely).
  React.useEffect(() => {
    if (!host || tab !== "comments") return;
    let cancelled = false;
    (async () => {
      setCommentsLoading(true);
      try {
        const data = await getHostComments(host);
        if (!cancelled) setComments(data);
      } catch (error) {
        if (!cancelled) handleError(error, "Error loading comments");
      } finally {
        if (!cancelled) setCommentsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [host, tab]);

  const setTab = React.useCallback(
    (next: string) => {
      if (!isTabKey(next) || next === tab) return;
      const p = new URLSearchParams(searchParams?.toString() ?? "");
      p.set("tab", next);
      router.replace(`${pathname}?${p.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams, tab],
  );

  // Clicking a proc row opens that frame's log. The frame-log viewer loads
  // its log content from the `frameLogDir` param, and a Proc carries the
  // absolute rqlog path directly (logPath), so no extra lookup is needed.
  const openProcLog = React.useCallback(
    (proc: Proc) => {
      if (!proc.logPath || !proc.frameName) return;
      const p = new URLSearchParams({
        frameLogDir: proc.logPath,
        username: currentUser,
      });
      router.push(`/frames/${encodeURIComponent(proc.frameName)}?${p.toString()}`);
    },
    [currentUser, router],
  );

  const openTagEditor = React.useCallback(() => {
    if (!host) return;
    window.dispatchEvent(
      new CustomEvent(OPEN_HOST_TAGS_EVENT, { detail: { hosts: [host] } }),
    );
  }, [host]);

  return (
    <div className="container mx-auto max-w-7xl py-6">
      <Breadcrumbs
        items={[{ label: "Hosts", href: "/hosts" }, { label: hostName || "Host" }]}
        className="mb-4"
      />

      <header className="mb-4 min-w-0">
        <h1 className="break-all text-2xl font-semibold">{hostName || "Host"}</h1>
        {host && (
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <Status status={host.state} />
            <Status status={host.lockState} />
            <span>
              {host.allocName ? `${host.allocName} - ` : ""}
              {host.os || "unknown OS"}
            </span>
          </p>
        )}
      </header>

      {hostLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-6 w-1/3" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : hostError || !host ? (
        <EmptyState
          icon={<Server className="h-8 w-8" aria-hidden="true" />}
          title="Host not found"
          description={
            hostError ??
            "We could not resolve this host. It may have been removed from Cuebot, or the URL may be incorrect."
          }
        />
      ) : (
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="flex flex-wrap">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="procs">Procs</TabsTrigger>
            <TabsTrigger value="comments">Comments</TabsTrigger>
            <TabsTrigger value="tags">Tags</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <OverviewPanel host={host} />
          </TabsContent>

          <TabsContent value="procs">
            {procsLoading ? (
              <TableSkeleton rows={6} />
            ) : (
              <SimpleDataTable
                data={procs}
                columns={procColumns}
                isProcsTable
                username={currentUser}
                onRowClick={openProcLog}
                columnVisibilityStorageKey="cueweb.host.procs.columnVisibility"
              />
            )}
            <p className="mt-2 text-xs text-muted-foreground">
              Click a proc to open its frame log. Refreshes every 15s.
            </p>
          </TabsContent>

          <TabsContent value="comments">
            {commentsLoading ? (
              <TableSkeleton rows={4} />
            ) : comments.length === 0 ? (
              <EmptyState
                icon={<MessageSquare className="h-8 w-8" aria-hidden="true" />}
                title="No comments"
                description="This host has no comments."
              />
            ) : (
              <ul className="divide-y divide-border rounded-lg border border-border">
                {comments.map((c) => (
                  <li key={c.id} className="px-3 py-2 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{c.subject || "(no subject)"}</span>
                      <span className="text-xs text-muted-foreground">
                        {c.user || "unknown"} - {formatTimestamp(c.timestamp)}
                      </span>
                    </div>
                    {c.message ? (
                      <p className="mt-1 whitespace-pre-wrap break-words text-xs text-muted-foreground">
                        {c.message}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </TabsContent>

          <TabsContent value="tags">
            <div className="mb-3 flex items-center justify-between gap-2">
              <p className="text-sm text-muted-foreground">
                {host.tags?.length ?? 0} {(host.tags?.length ?? 0) === 1 ? "tag" : "tags"}
              </p>
              <Button variant="outline" size="sm" onClick={openTagEditor}>
                <Tag className="mr-2 h-4 w-4" aria-hidden="true" />
                Edit tags
              </Button>
            </div>
            {!host.tags || host.tags.length === 0 ? (
              <EmptyState
                icon={<Tag className="h-8 w-8" aria-hidden="true" />}
                title="No tags"
                description="This host has no tags. Use Edit tags to add some."
              />
            ) : (
              <div className="flex flex-wrap gap-2">
                {host.tags.map((t) => (
                  <span
                    key={t}
                    className="inline-flex items-center rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs font-medium"
                  >
                    {t}
                  </span>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      )}

      {/* Tag editor opened from the Tags tab or the hosts-list context menu. */}
      <EditHostTagsDialog />
    </div>
  );
}

function TableSkeleton({ rows }: { rows: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-8 w-full" />
      ))}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function OverviewPanel({ host }: { host: Host }) {
  return (
    <div className="space-y-6">
      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Identity
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="State" value={<Status status={host.state} />} />
          <Stat label="Locked" value={<Status status={host.lockState} />} />
          <Stat label="NIMBY" value={host.nimbyEnabled ? "Yes" : "No"} />
          <Stat label="Allocation" value={host.allocName || "-"} />
          <Stat label="OS" value={host.os || "-"} />
          <Stat label="Load" value={host.load ?? "-"} />
          <Stat label="Thread mode" value={host.threadMode || "-"} />
          <Stat label="Boot time" value={formatTimestamp(host.bootTime)} />
          <Stat label="Last ping" value={formatTimestamp(host.pingTime)} />
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Resources
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          <Stat label="Cores (Idle/Total)" value={`${host.idleCores.toFixed(2)} / ${host.cores.toFixed(2)}`} />
          <Stat
            label="Memory (Idle/Total)"
            value={`${kbStringToHuman(host.idleMemory)} / ${kbStringToHuman(host.totalMemory)}`}
          />
          <Stat label="Free /mcp" value={kbStringToHuman(host.freeMcp)} />
          <Stat
            label="GPUs (Idle/Total)"
            value={
              host.gpus === undefined
                ? "-"
                : `${(host.idleGpus ?? 0).toFixed(2)} / ${host.gpus.toFixed(2)}`
            }
          />
        </div>
      </section>
    </div>
  );
}
