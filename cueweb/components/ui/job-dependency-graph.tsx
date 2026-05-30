"use client";

import React, { useEffect, useState } from 'react';
import { ReactFlow, Background, Controls, Edge, Node, Position } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { Job } from '@/app/jobs/columns';
import { Depend, getDependsForJob } from '@/app/utils/get_utils';
import { toastSuccess } from '@/app/utils/notify_utils';
import { useTheme } from "next-themes";

type JobDependencyGraphProps = {
  job: Job;
  onNavigate?: (nodeId: string) => void;
};

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 200;
const nodeHeight = 80;

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
  dagreGraph.setGraph({ rankdir: direction });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const newNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const newNode = {
      ...node,
      targetPosition: Position.Top,
      sourcePosition: Position.Bottom,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };

    return newNode;
  });

  return { nodes: newNodes, edges };
};

export function JobDependencyGraph({ job, onNavigate }: JobDependencyGraphProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [loading, setLoading] = useState(true);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    const loadGraph = async () => {
      setLoading(true);
      try {
        const depends = await getDependsForJob(job.id);
        
        const rawNodes = new Map<string, Node>();
        const rawEdges: Edge[] = [];

        const isDark = resolvedTheme === 'dark';

        const addNode = (id: string, label: string) => {
          if (id && !rawNodes.has(id)) {
            rawNodes.set(id, {
              id,
              position: { x: 0, y: 0 },
              data: { label },
              style: { 
                background: isDark ? '#1e293b' : '#f1f5f9', 
                color: isDark ? '#f8fafc' : '#0f172a', 
                border: isDark ? '1px solid #475569' : '1px solid #cbd5e1',
                borderRadius: '6px',
                padding: '10px',
                fontSize: '12px',
                width: nodeWidth,
                wordBreak: 'break-all',
                textAlign: 'center'
              }
            });
          }
        };

        depends.forEach((dep) => {
          const dependOn = dep.dependOnFrame || dep.dependOnLayer || dep.dependOnJob;
          const dependEr = dep.dependErFrame || dep.dependErLayer || dep.dependErJob;

          if (dependOn && dependEr) {
            addNode(dependOn, dependOn);
            addNode(dependEr, dependEr);

            rawEdges.push({
              id: dep.id,
              source: dependOn,
              target: dependEr,
              animated: dep.active,
              style: { stroke: isDark ? '#94a3b8' : '#64748b' }
            });
          }
        });

        if (rawNodes.size > 0) {
            const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
              Array.from(rawNodes.values()),
              rawEdges
            );
            setNodes(layoutedNodes);
            setEdges(layoutedEdges);
        }
      } catch (e) {
        console.error("Failed to load dependencies", e);
      }
      setLoading(false);
    };
    
    loadGraph();
  }, [job.id, resolvedTheme]);

  const handleNodeClick = React.useCallback((event: React.MouseEvent, node: Node) => {
    toastSuccess(`Navigating to ${node.id}...`);
    if (onNavigate) {
      onNavigate(node.id);
    }
  }, [onNavigate]);

  if (loading) {
    return <div className="w-full h-[600px] flex items-center justify-center text-muted-foreground">Loading dependency graph...</div>;
  }

  if (nodes.length === 0) {
    return <div className="w-full h-[600px] flex items-center justify-center text-muted-foreground">No dependencies found for this job.</div>;
  }

  const cursorColor = resolvedTheme === 'dark' ? 'white' : 'black';
  // Use a custom SVG crosshair cursor that matches the theme contrast
  const cursorSvg = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="${cursorColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>`;

  return (
    <div style={{ width: '100%', height: '600px' }} className="border rounded-md">
      <style>{`
        .react-flow__pane, .react-flow__pane.dragging {
          cursor: url('${cursorSvg}') 12 12, crosshair !important;
        }
      `}</style>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        colorMode={resolvedTheme === 'dark' ? 'dark' : 'light'}
        onNodeClick={handleNodeClick}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
