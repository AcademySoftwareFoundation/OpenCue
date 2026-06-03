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

// Serializes a Job + Layers payload into the cuebot job-spec XML
// (OpenCue Job Specification Language - cjsl). Port of the relevant
// parts of pyoutline/outline/backend/cue.py:_serialize.
//
// Submit path: /api/job/submit -> /job.JobInterface/LaunchSpecAndWait
// expects a single `spec` string containing this XML.

import { SPEC_VERSION } from "./constants";
import { buildLayerCommand } from "./commands";
import type { JobInfo, LayerInput } from "./schemas";

// Cuebot refuses to launch jobs as root (uid=0). pyoutline uses
// os.getuid() which is the real numeric uid of whoever invoked it; in
// the browser we don't have one, so derive a stable, non-zero UID from
// the username. Same username always maps to the same UID, so cuebot's
// per-user accounting still works.
function uidForUser(username: string): number {
  // Simple FNV-1a-style hash, clamped to [1000, 65000] to avoid the
  // 0-999 system-reserved range and stay below the typical 16-bit
  // ceiling cuebot writes into the DB.
  let hash = 2166136261;
  for (let i = 0; i < username.length; i++) {
    hash ^= username.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return 1000 + (Math.abs(hash) % 64000);
}

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function el(tag: string, content: string | number, attrs?: Record<string, string>): string {
  const attrStr = attrs
    ? Object.entries(attrs)
        .map(([k, v]) => ` ${k}="${escapeXml(v)}"`)
        .join("")
    : "";
  return `<${tag}${attrStr}>${escapeXml(String(content))}</${tag}>`;
}

function emptyEl(tag: string): string {
  return `<${tag}/>`;
}

function layerToXml(layer: LayerInput, index: number, prevLayer: LayerInput | null): string {
  const command = buildLayerCommand(layer, { silent: false });
  const services = layer.services.length > 0 ? layer.services : ["default"];
  const lines: string[] = [];

  lines.push(`<layer name="${escapeXml(layer.name)}" type="Render">`);
  lines.push(`  ${el("cmd", command)}`);
  lines.push(`  ${el("range", layer.frameSpec)}`);
  lines.push(`  ${el("chunk", layer.chunkSize)}`);

  if (layer.overrideCores) {
    lines.push(`  ${el("cores", Number(layer.cores).toFixed(1))}`);
    // pyoutline mirrors cuesubmit's threadable heuristic: if the user
    // pinned cores >= 2 or set 0 (= "use any"), the layer is marked
    // threadable. Re-implement here so the dispatcher behaves the same
    // as a CueGUI submit.
    const threadable = Number(layer.cores) >= 2 || Number(layer.cores) <= 0;
    lines.push(`  ${el("threadable", threadable ? "True" : "False")}`);
  }

  // Memory request per frame. Empty -> let cuebot use the service's
  // int_mem_min (3.2 GB for the seeded `default` service, which keeps
  // trivial jobs stuck in WAITING on small RQDs).
  if (layer.memory && layer.memory.trim()) {
    lines.push(`  ${el("memory", layer.memory.trim())}`);
  }

  lines.push(`  <env/>`);
  lines.push(`  <services>`);
  for (const svc of services) {
    lines.push(`    ${el("service", svc)}`);
  }
  lines.push(`  </services>`);

  if (layer.limits.length > 0) {
    lines.push(`  <limits>`);
    for (const limit of layer.limits) {
      lines.push(`    ${el("limit", limit)}`);
    }
    lines.push(`  </limits>`);
  }

  lines.push(`</layer>`);

  return lines.join("\n");
}

function dependsToXml(jobName: string, layers: ReadonlyArray<LayerInput>): string[] {
  const lines: string[] = [];
  for (let i = 1; i < layers.length; i++) {
    const layer = layers[i];
    const prev = layers[i - 1];
    if (!layer.dependencyType) continue;
    // Cuebot dep types: LAYER_ON_LAYER (Layer) -> entire previous layer must finish
    //                   FRAME_BY_FRAME (Frame) -> same frame in prev layer
    const type =
      layer.dependencyType === "Layer" ? "LAYER_ON_LAYER" : "FRAME_BY_FRAME";
    lines.push(
      `<depend type="${type}" anyframe="False">`,
    );
    // depjob / onjob are mandatory and must resolve to a real job: cuebot
    // pipes both through JobSpec.conformJobName, which throws on anything
    // shorter than 3 chars (empty included). For an intra-spec depend
    // they're always *this* job - pyoutline emits `ol.get_name()` for
    // both in outline/backend/cue.py:478-487 and we mirror that here.
    // deplayer = the dependent (current layer, which has to wait)
    // onlayer  = the layer being waited on (the previous one)
    lines.push(`  ${el("depjob", jobName)}`);
    lines.push(`  ${el("deplayer", layer.name)}`);
    lines.push(`  ${el("onjob", jobName)}`);
    lines.push(`  ${el("onlayer", prev.name)}`);
    lines.push(`</depend>`);
  }
  return lines;
}

/**
 * Build the OpenCue job-spec XML. The body matches what pyoutline's
 * outline.backend.cue.serialize emits for an equivalent CueGUI submit,
 * so the resulting cuebot job is indistinguishable from a CueGUI one.
 */
export function buildJobSpecXml(job: JobInfo, layers: ReadonlyArray<LayerInput>): string {
  const out: string[] = [];
  out.push(`<?xml version="1.0"?>`);
  out.push(
    `<!DOCTYPE spec PUBLIC "SPI Cue  Specification Language" ` +
      `"http://localhost:8080/spcue/dtd/cjsl-${SPEC_VERSION}.dtd">`,
  );
  out.push(`<spec>`);

  // Always emit a facility, defaulting to "local" when the user
  // picked [Default]. Omitting the element lets cuebot fall back to
  // its own default which is "cloud" in the seeded sandbox - that
  // never matches the only RQD host's `local.general` allocation, so
  // every submission would sit in WAITING forever. Operators with
  // multi-facility deployments override via the dropdown.
  out.push(`  ${el("facility", job.facility || "local")}`);
  out.push(`  ${el("show", job.show)}`);
  out.push(`  ${el("shot", job.shot)}`);
  out.push(`  ${el("user", job.user)}`);
  // Stable non-zero UID derived from the username. Cuebot rejects 0
  // with "Cannot launch jobs as root", so we never emit it.
  out.push(`  ${el("uid", String(uidForUser(job.user)))}`);
  out.push(`  <job name="${escapeXml(job.name)}">`);
  out.push(`    <paused>False</paused>`);
  out.push(`    <maxretries>2</maxretries>`);
  out.push(`    <env/>`);
  out.push(`    <layers>`);
  for (let i = 0; i < layers.length; i++) {
    const layerXml = layerToXml(layers[i], i, i > 0 ? layers[i - 1] : null);
    // Indent the layer block under <layers>.
    out.push(layerXml.split("\n").map((l) => `      ${l}`).join("\n"));
  }
  out.push(`    </layers>`);
  out.push(`  </job>`);

  const dependLines = dependsToXml(job.name, layers);
  if (dependLines.length > 0) {
    out.push(`  <depends>`);
    for (const line of dependLines) {
      out.push(line.split("\n").map((l) => `    ${l}`).join("\n"));
    }
    out.push(`  </depends>`);
  } else {
    out.push(`  ${emptyEl("depends")}`);
  }

  out.push(`</spec>`);
  return out.join("\n");
}
