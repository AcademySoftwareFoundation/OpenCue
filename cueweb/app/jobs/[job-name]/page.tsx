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

import { Frame, frameColumns } from "@/app/frames/frame-columns";
import { Job, getState } from "@/app/jobs/columns";
import { Layer, layerColumns } from "@/app/layers/layer-columns";
import { UNKNOWN_USER } from "@/app/utils/constants";
import {
  JobComment,
  getFramesForJob,
  getJob,
  getJobComments,
  getJobs,
  getLayersForJob,
} from "@/app/utils/get_utils";
import {
  convertMemoryToString,
  secondsToHHHMM,
  secondsToHumanAge,
} from "@/app/utils/layers_frames_utils";
import { handleError } from "@/app/utils/notify_utils";
import { Breadcrumbs } from "@/components/ui/breadcrumbs";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { SimpleDataTable } from "@/components/ui/simple-data-table";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileX, GitFork, MessageSquare } from "lucide-react";
import Link from "next/link";
import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";
import * as React from "react";

const TAB_KEYS = ["overview", "layers", "frames", "comments", "dependencies"] as const;
type TabKey = (typeof TAB_KEYS)[number];

const isTabKey = (value: string | null | undefined): value is TabKey =>
  !!value && (TAB_KEYS as readonly string[]).includes(value);

function formatTimestamp(unixSeconds: number | undefined): string {
  if (!unixSeconds) return "-";
  return new Date(unixSeconds * 1000).toLocaleString();
}

export default function JobDetailPage() {
  const params = useParams<{ "job-name": string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const jobName = decodeURIComponent(params?.["job-name"] ?? "");
  const jobIdParam = searchParams.get("jobId") ?? "";
  const tabParam = searchParams.get("tab");
  const tab: TabKey = isTabKey(tabParam) ? tabParam : "overview";

  const [job, setJob] = React.useState<Job | null>(null);
  const [jobLoading, setJobLoading] = React.useState(true);
  const [jobError, setJobError] = React.useState<string | null>(null);

  const [layers, setLayers] = React.useState<Layer[]>([]);
  const [frames, setFrames] = React.useState<Frame[]>([]);
  const [comments, setComments] = React.useState<JobComment[]>([]);
  const [layersLoading, setLayersLoading] = React.useState(false);
  const [framesLoading, setFramesLoading] = React.useState(false);
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
        // Leave as UNKNOWN_USER; this only governs client-side context-menu
        // affordances. Cuebot enforces ownership server-side.
      }
    })();
  }, []);

  // Resolve the job: prefer the jobId query (cheap, exact). Fall back to a
  // regex lookup against the URL-segment name so the page is reachable by
  // typing /jobs/<name> without a jobId.
  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      setJobLoading(true);
      setJobError(null);
      try {
        let fetched: Job | null = null;
        if (jobIdParam) {
          fetched = await getJob(jobIdParam);
        }
        if (!fetched && jobName) {
          const escaped = jobName.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&");
          const body = JSON.stringify({
            r: { include_finished: true, regex: [`^${escaped}$`] },
          });
          const matches = await getJobs(body);
          fetched = matches.length ? matches[0] : null;
        }
        if (cancelled) return;
        if (!fetched) {
          setJobError("Job not found.");
          setJob(null);
        } else {
          setJob(fetched);
        }
      } catch (error) {
        if (cancelled) return;
        handleError(error, "Error loading job");
        setJobError("Error loading job.");
      } finally {
        if (!cancelled) setJobLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [jobIdParam, jobName]);

  // Lazy-load each tab's data: only fetch when its tab is first opened, then
  // refresh on a 5s interval while it stays the active tab.
  const loadedTabs = React.useRef(new Set<TabKey>());

  React.useEffect(() => {
    if (!job) return;
    if (tab === "overview") return;

    let cancelled = false;
    const firstLoad = !loadedTabs.current.has(tab);

    const runFetch = async () => {
      try {
        if (tab === "layers") {
          if (firstLoad) setLayersLoading(true);
          const data = await getLayersForJob(job);
          if (!cancelled) setLayers(data);
        } else if (tab === "frames") {
          if (firstLoad) setFramesLoading(true);
          const data = await getFramesForJob(job);
          if (!cancelled) setFrames(data);
        } else if (tab === "comments") {
          if (firstLoad) setCommentsLoading(true);
          const data = await getJobComments(job);
          if (!cancelled) setComments(data);
        }
      } catch (error) {
        if (!cancelled) handleError(error, `Error loading ${tab}`);
      } finally {
        if (!cancelled) {
          loadedTabs.current.add(tab);
          if (tab === "layers") setLayersLoading(false);
          if (tab === "frames") setFramesLoading(false);
          if (tab === "comments") setCommentsLoading(false);
        }
      }
    };

    runFetch();
    const interval = setInterval(runFetch, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [job, tab]);

  const setTab = React.useCallback(
    (next: string) => {
      if (!isTabKey(next) || next === tab) return;
      const params = new URLSearchParams(searchParams?.toString() ?? "");
      params.set("tab", next);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams, tab],
  );

  return (
    <div className="container mx-auto py-6 max-w-7xl">
      <Breadcrumbs
        items={[{ label: "Jobs", href: "/" }, { label: jobName || "Job" }]}
        className="mb-4"
      />

      <header className="mb-4">
        <h1 className="text-2xl font-semibold break-all">{jobName || "Job"}</h1>
        {job && (
          <p className="mt-1 text-sm text-muted-foreground">
            {getState(job)} - {job.show} / {job.shot} - owned by {job.user}
          </p>
        )}
      </header>

      {jobLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-6 w-1/3" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : jobError || !job ? (
        <EmptyState
          icon={<FileX className="h-8 w-8" aria-hidden="true" />}
          title="Job not found"
          description={
            jobError ??
            "We could not resolve this job. The job may have been removed, or the URL may be incorrect."
          }
        />
      ) : (
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="flex flex-wrap">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="layers">Layers</TabsTrigger>
            <TabsTrigger value="frames">Frames</TabsTrigger>
            <TabsTrigger value="comments">Comments</TabsTrigger>
            <TabsTrigger value="dependencies">Dependencies</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <OverviewPanel job={job} />
          </TabsContent>

          <TabsContent value="layers">
            {layersLoading ? (
              <TableSkeleton rows={6} />
            ) : layers.length === 0 ? (
              <EmptyState
                icon={<FileX className="h-8 w-8" aria-hidden="true" />}
                title="No layers"
                description="This job does not have any layers yet."
              />
            ) : (
              <SimpleDataTable data={layers} columns={layerColumns} username={currentUser} />
            )}
          </TabsContent>

          <TabsContent value="frames">
            {framesLoading ? (
              <TableSkeleton rows={10} />
            ) : frames.length === 0 ? (
              <EmptyState
                icon={<FileX className="h-8 w-8" aria-hidden="true" />}
                title="No frames"
                description="This job has not produced any frames yet."
              />
            ) : (
              <SimpleDataTable
                data={frames}
                columns={frameColumns}
                job={job}
                isFramesTable={true}
                username={currentUser}
              />
            )}
          </TabsContent>

          <TabsContent value="comments">
            <CommentsTab
              job={job}
              comments={comments}
              loading={commentsLoading}
            />
          </TabsContent>

          <TabsContent value="dependencies">
            <EmptyState
              icon={<GitFork className="h-8 w-8" aria-hidden="true" />}
              title="Dependencies"
              description="Job dependency visualization will land in a follow-up task. For now, use CueGUI's Dependency Wizard for cross-job links."
            />
          </TabsContent>
        </Tabs>
      )}
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

function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 text-lg font-semibold tabular-nums">{value}</div>
      {hint ? <div className="mt-0.5 text-xs text-muted-foreground">{hint}</div> : null}
    </div>
  );
}

function OverviewPanel({ job }: { job: Job }) {
  const stats = job.jobStats;
  const ageSec =
    job.stopTime && job.stopTime > 0
      ? job.stopTime - job.startTime
      : Math.max(0, Math.floor(Date.now() / 1000) - job.startTime);

  return (
    <div className="space-y-6">
      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Identity
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="State" value={getState(job)} />
          <Stat label="Show / Shot" value={`${job.show} / ${job.shot}`} />
          <Stat label="Owner" value={job.user} />
          <Stat label="Facility" value={job.facility || "-"} />
          <Stat label="OS" value={job.os || "-"} />
          <Stat label="Priority" value={job.priority} />
          <Stat label="Started" value={formatTimestamp(job.startTime)} />
          <Stat
            label="Stopped"
            value={job.stopTime ? formatTimestamp(job.stopTime) : "running"}
          />
          <Stat label="Age" value={secondsToHumanAge(ageSec)} />
          <Stat label="Auto-eat" value={job.autoEat ? "On" : "Off"} />
          <Stat label="Paused" value={job.isPaused ? "Yes" : "No"} />
          <Stat label="Group" value={job.group || "-"} />
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Frames
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <Stat label="Total" value={stats.totalFrames} />
          <Stat label="Running" value={stats.runningFrames} />
          <Stat label="Waiting" value={stats.waitingFrames} />
          <Stat label="Succeeded" value={stats.succeededFrames} />
          <Stat label="Dead" value={stats.deadFrames} />
          <Stat label="Eaten" value={stats.eatenFrames} />
          <Stat label="Pending" value={stats.pendingFrames} />
          <Stat label="Dependent" value={stats.dependFrames} />
          <Stat label="Layers" value={stats.totalLayers} />
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Resources
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          <Stat label="Reserved cores" value={stats.reservedCores} />
          <Stat label="Reserved GPUs" value={stats.reservedGpus} />
          <Stat label="Min / Max cores" value={`${job.minCores} / ${job.maxCores}`} />
          <Stat label="Min / Max GPUs" value={`${job.minGpus} / ${job.maxGpus}`} />
          <Stat
            label="Max RSS"
            value={convertMemoryToString(Number.parseInt(stats.maxRss), JSON.stringify(job))}
          />
          <Stat
            label="Max GPU mem"
            value={convertMemoryToString(Number.parseInt(stats.maxGpuMemory), JSON.stringify(job))}
          />
          <Stat label="Avg frame" value={secondsToHHHMM(stats.avgFrameSec)} />
          <Stat label="High frame" value={secondsToHHHMM(stats.highFrameSec)} />
          <Stat label="Avg core" value={secondsToHHHMM(stats.avgCoreSec)} />
        </div>
      </section>
    </div>
  );
}

function CommentsTab({
  job,
  comments,
  loading,
}: {
  job: Job;
  comments: JobComment[];
  loading: boolean;
}) {
  const fullPageHref = `/jobs/${encodeURIComponent(job.name)}/comments?jobId=${encodeURIComponent(job.id)}`;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          {comments.length} {comments.length === 1 ? "comment" : "comments"}
        </p>
        <Button asChild variant="outline" size="sm">
          <Link href={fullPageHref}>Open full comments page</Link>
        </Button>
      </div>

      {loading ? (
        <TableSkeleton rows={4} />
      ) : comments.length === 0 ? (
        <EmptyState
          icon={<MessageSquare className="h-8 w-8" aria-hidden="true" />}
          title="No comments"
          description="Add a comment from the full comments page."
        />
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border">
          {comments.map((c) => (
            <li key={c.id} className="px-3 py-2 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium truncate">{c.subject || "(no subject)"}</span>
                <span className="text-xs text-muted-foreground">
                  {c.user || "unknown"} - {formatTimestamp(c.timestamp)}
                </span>
              </div>
              {c.message ? (
                <p className="mt-1 text-xs text-muted-foreground line-clamp-2 break-words">
                  {c.message}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
