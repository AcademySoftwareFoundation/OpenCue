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

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Background,
  Controls,
  Edge,
  Handle,
  Node,
  NodeProps,
  Position,
  ReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "dagre";
import { useTheme } from "next-themes";

import { Job } from "@/app/jobs/columns";
import { Depend } from "@/app/utils/get_utils";

// Silent POST that intentionally bypasses accessGetApi - the BFS below
// expects partial failure (some jobs in the tree may have been
// unmonitored, finished + pruned, or be in a different show). Routing
// through accessGetApi would fire a handleError() toast for every miss,
// which surfaced as the cascade of "Resource not found" red toasts in
// the original implementation.
async function silentPost(endpoint: string, body: object): Promise<any> {
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: JSON.stringify(body),
    });
    if (!res.ok) return null;
    const json = await res.json();
    if (json?.error) return null;
    return json.data;
  } catch {
    return null;
  }
}

const REGEX_ESCAPE_RE = /[.*+?^${}()|[\]\\]/g;
function escapeRegex(s: string): string {
  return s.replace(REGEX_ESCAPE_RE, "\\$&");
}

// Resolves a job name to its UUID via /api/job/getjobs with an
// anchored-regex match. Cuebot's GetDepends / GetWhatDependsOnThis RPCs
// require a real UUID (curling them with `{name}` only returns
// "Job not found"), so each BFS hop has to do this lookup first. We
// memoize via the supplied Map so a chain of N jobs costs N resolves
// across the whole walk, not N per hop.
async function resolveJobIdByName(
  name: string,
  cache: Map<string, string | null>,
): Promise<string | null> {
  if (cache.has(name)) return cache.get(name) ?? null;
  const data = await silentPost("/api/job/getjobs", {
    r: { include_finished: true, regex: [`^${escapeRegex(name)}$`] },
  });
  const list = Array.isArray(data) ? data : data?.jobs?.jobs;
  const id = (list && list[0]?.id) ?? null;
  cache.set(name, id);
  return id;
}

async function silentGetDepends(jobId: string): Promise<Depend[]> {
  const data = await silentPost("/api/job/action/getdepends", { job: { id: jobId } });
  if (!data) return [];
  const seq = data?.depends?.depends ?? data?.depends ?? data;
  return Array.isArray(seq) ? (seq as Depend[]) : [];
}

async function silentGetWhatDependsOnThis(jobId: string): Promise<Depend[]> {
  const data = await silentPost("/api/job/action/getwhatdependsonthis", {
    job: { id: jobId },
  });
  if (!data) return [];
  const seq = data?.depends?.depends ?? data?.depends ?? data;
  if (!Array.isArray(seq)) return [];
  // Mirror the Group-By Dependent tree behavior: only active depends
  // contribute children. Satisfied / dropped depends shouldn't keep
  // ghost nodes in the graph.
  return seq.filter((d: any) => d?.active !== false) as Depend[];
}

type JobDependencyGraphProps = {
  job: Job;
  // Optional callback fired with the clicked node's job name. The graph
  // itself does not navigate by default - the parent component decides
  // (e.g. setDetailJob, router.push, etc).
  onNodeNavigate?: (jobName: string) => void;
  // Max recursion depth when walking the dep tree. 4-6 keeps wide chains
  // performant without missing typical render-farm topologies.
  maxDepth?: number;
};

// Layout config. Node sizes are estimates used by dagre to compute
// positions; the actual node component below uses CSS to size itself,
// with these values driving the spacing dagre allocates.
const NODE_WIDTH = 260;
const NODE_HEIGHT = 64;

type NodeKind = "JOB" | "LAYER" | "FRAME";

type GraphNodeData = {
  label: string;
  fullName: string;
  kind: NodeKind;
  jobName?: string;
  isFocus: boolean;
};

// Custom node renderer: monospace, truncates long names, full text in
// title tooltip, kind-aware colored left border. The focus node (the job
// the panel was opened for) gets a stronger ring.
function DependencyNode({ data, selected }: NodeProps) {
  const d = data as unknown as GraphNodeData;
  const accent =
    d.kind === "JOB"
      ? "border-l-blue-500"
      : d.kind === "LAYER"
        ? "border-l-amber-500"
        : "border-l-emerald-500";
  return (
    <div
      title={d.fullName}
      className={`rounded-md border bg-card text-card-foreground border-l-4 ${accent} px-3 py-2 shadow-sm ${
        d.isFocus ? "ring-2 ring-primary" : ""
      } ${selected ? "ring-2 ring-primary/60" : ""}`}
      style={{ width: NODE_WIDTH, fontFamily: "ui-monospace,monospace" }}
    >
      <Handle type="target" position={Position.Top} className="!bg-muted-foreground" />
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-muted-foreground">
        <span>{d.kind}</span>
      </div>
      <div className="truncate text-xs">{d.label}</div>
      <Handle type="source" position={Position.Bottom} className="!bg-muted-foreground" />
    </div>
  );
}

const nodeTypes = { dep: DependencyNode };

// Pure dagre layout. Creates a fresh graph instance per call so two
// graphs on the page (or two consecutive layouts) never share state.
// This was the module-level singleton bug in the original.
function layoutNodes(nodes: Node[], edges: Edge[], direction: "TB" | "LR" = "TB") {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: direction, nodesep: 32, ranksep: 56 });

  for (const n of nodes) {
    g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const e of edges) {
    g.setEdge(e.source, e.target);
  }
  dagre.layout(g);

  return nodes.map((n) => {
    const p = g.node(n.id);
    return {
      ...n,
      targetPosition: Position.Top,
      sourcePosition: Position.Bottom,
      position: {
        x: (p?.x ?? 0) - NODE_WIDTH / 2,
        y: (p?.y ?? 0) - NODE_HEIGHT / 2,
      },
    } as Node;
  });
}

// Build a (nodeId, label, kind) for a depend's endpoint. Prefers the
// most-specific identifier but constructs a hierarchical label so the
// user can tell a frame's job/layer context at a glance (the original
// component dropped that context).
function describeEndpoint(
  jobName: string,
  layerName: string,
  frameName: string,
): { id: string; label: string; kind: NodeKind; jobName: string } {
  if (frameName) {
    return {
      id: `frame:${jobName}/${layerName}/${frameName}`,
      label: `${frameName}\n${layerName} | ${jobName}`,
      kind: "FRAME",
      jobName,
    };
  }
  if (layerName) {
    return {
      id: `layer:${jobName}/${layerName}`,
      label: `${layerName}\n${jobName}`,
      kind: "LAYER",
      jobName,
    };
  }
  return { id: `job:${jobName}`, label: jobName, kind: "JOB", jobName };
}

// Adds (or merges) one Depend into the running node/edge maps. Returns
// the depend-er and depend-on jobNames so the BFS frontier can expand.
function ingestDepend(
  dep: Depend,
  nodes: Map<string, Node>,
  edges: Map<string, Edge>,
  focusJobName: string,
): { erJob: string; onJob: string } | null {
  const er = describeEndpoint(dep.dependErJob, dep.dependErLayer, dep.dependErFrame);
  const on = describeEndpoint(dep.dependOnJob, dep.dependOnLayer, dep.dependOnFrame);
  if (!er.jobName || !on.jobName) return null;

  for (const ep of [er, on]) {
    if (!nodes.has(ep.id)) {
      nodes.set(ep.id, {
        id: ep.id,
        type: "dep",
        position: { x: 0, y: 0 },
        data: {
          label: ep.label,
          fullName: ep.label,
          kind: ep.kind,
          jobName: ep.jobName,
          isFocus: ep.jobName === focusJobName && ep.kind === "JOB",
        } satisfies GraphNodeData,
      } as Node);
    }
  }

  // Edge direction: the dependent (er) waits on the upstream (on),
  // so visual flow is upstream -> downstream (top-to-bottom).
  const edgeId = dep.id || `${on.id}__${er.id}`;
  if (!edges.has(edgeId)) {
    edges.set(edgeId, {
      id: edgeId,
      source: on.id,
      target: er.id,
      animated: dep.active,
    } as Edge);
  }

  return { erJob: er.jobName, onJob: on.jobName };
}

// Recursively walk the dependency tree starting from `focus`. Follows
// both directions (what this job depends on AND what depends on this
// job), bounded by maxDepth and a visited-job set to prevent infinite
// recursion on cycles. Mirrors CueGUI's
// `JobMonitorGraph.getRecursiveDependentJobs` behavior.
//
// Each BFS hop has to resolve the job's UUID first (cuebot rejects
// name-only depend lookups with "Job not found"). The resolved IDs are
// cached so a 12-job chain costs ~12 GetJobs lookups across the whole
// walk, not 12 per hop.
async function walkDependencyTree(
  focus: Job,
  maxDepth: number,
): Promise<{ nodes: Node[]; edges: Edge[] }> {
  const nodeMap = new Map<string, Node>();
  const edgeMap = new Map<string, Edge>();
  const idCache = new Map<string, string | null>([[focus.name, focus.id]]);

  // Always insert the focus job so an isolated job still renders one node.
  const focusEp = describeEndpoint(focus.name, "", "");
  nodeMap.set(focusEp.id, {
    id: focusEp.id,
    type: "dep",
    position: { x: 0, y: 0 },
    data: {
      label: focus.name,
      fullName: focus.name,
      kind: "JOB",
      jobName: focus.name,
      isFocus: true,
    } satisfies GraphNodeData,
  } as Node);

  const visited = new Set<string>([focus.name]);
  let frontier: string[] = [focus.name];

  for (let depth = 0; depth < maxDepth && frontier.length > 0; depth += 1) {
    // Resolve every frontier name to an id (cached). Misses just become
    // null and the corresponding hop is skipped silently - typically
    // because the dependent / depended job is in a different show.
    const ids = await Promise.all(
      frontier.map((name) => resolveJobIdByName(name, idCache)),
    );

    // Fetch the two directions in parallel per resolved id.
    const depsPerJob = await Promise.all(
      frontier.map(async (_name, i) => {
        const id = ids[i];
        if (!id) return [] as Depend[];
        const [downstream, upstream] = await Promise.all([
          silentGetDepends(id),
          silentGetWhatDependsOnThis(id),
        ]);
        return [...downstream, ...upstream];
      }),
    );

    const nextFrontier: string[] = [];
    for (const deps of depsPerJob) {
      for (const dep of deps) {
        const ingested = ingestDepend(dep, nodeMap, edgeMap, focus.name);
        if (!ingested) continue;
        for (const j of [ingested.erJob, ingested.onJob]) {
          if (!visited.has(j)) {
            visited.add(j);
            nextFrontier.push(j);
          }
        }
      }
    }
    frontier = nextFrontier;
  }

  return { nodes: Array.from(nodeMap.values()), edges: Array.from(edgeMap.values()) };
}

export function JobDependencyGraph({
  job,
  onNodeNavigate,
  maxDepth = 4,
}: JobDependencyGraphProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [loading, setLoading] = useState(true);
  const { resolvedTheme } = useTheme();
  const router = useRouter();
  const instanceIdRef = useRef(
    `dep-graph-${Math.random().toString(36).slice(2, 10)}`,
  );

  // Data fetch + layout - keyed only on job.id, so flipping the theme
  // toggle doesn't re-fetch every depend in the tree.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    walkDependencyTree(job, maxDepth)
      .then(({ nodes: rawNodes, edges: rawEdges }) => {
        if (cancelled) return;
        const laid = layoutNodes(rawNodes, rawEdges);
        setNodes(laid);
        setEdges(rawEdges);
      })
      .catch((e) => {
        console.error("Failed to build dependency graph", e);
        if (!cancelled) {
          setNodes([]);
          setEdges([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [job.id, job.name, maxDepth]);

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const data = node.data as unknown as GraphNodeData;
      // Prefer parent-supplied navigation; otherwise navigate to the
      // tabbed job-detail page so the click actually does something
      // useful (the original component fired a misleading toast).
      if (onNodeNavigate) {
        onNodeNavigate(data.jobName ?? data.label);
        return;
      }
      const target = data.jobName;
      if (target) router.push(`/jobs/${encodeURIComponent(target)}?tab=overview`);
    },
    [onNodeNavigate, router],
  );

  // Theme-scoped cursor URL. Memoized per theme + per instance so two
  // graphs on the page don't fight each other and the SVG isn't rebuilt
  // every render. CSS selector is namespaced via `data-graph-id` so the
  // cursor only applies to *this* instance.
  const cursorColor = resolvedTheme === "dark" ? "white" : "black";
  const cursorCss = useMemo(() => {
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='${cursorColor}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><line x1='12' y1='5' x2='12' y2='19'></line><line x1='5' y1='12' x2='19' y2='12'></line></svg>`;
    const url = `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
    return `[data-graph-id="${instanceIdRef.current}"] .react-flow__pane,[data-graph-id="${instanceIdRef.current}"] .react-flow__pane.dragging{cursor:url('${url}') 12 12,crosshair !important;}`;
  }, [cursorColor]);

  if (loading) {
    return (
      <div className="flex h-[400px] w-full items-center justify-center text-muted-foreground">
        Loading dependency graph...
      </div>
    );
  }

  if (nodes.length <= 1) {
    return (
      <div className="flex h-[200px] w-full items-center justify-center text-muted-foreground">
        No dependencies found for this job.
      </div>
    );
  }

  return (
    <div
      data-graph-id={instanceIdRef.current}
      style={{ width: "100%", height: 480 }}
      className="rounded-md border border-border"
    >
      <style>{cursorCss}</style>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        colorMode={resolvedTheme === "dark" ? "dark" : "light"}
        onNodeClick={handleNodeClick}
        proOptions={{ hideAttribution: true }}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
