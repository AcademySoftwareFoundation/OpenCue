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

/**
 * Thin client for the Loki HTTP API used to display frame logs.
 *
 * When `NEXT_PUBLIC_LOKI_URL` is set, CueWeb queries Loki for a frame's log
 * lines instead of reading the `.rqlog` file from disk. This mirrors CueGUI's
 * `LokiViewPlugin` (cuegui/cuegui/plugins/LokiViewPlugin.py): RQD ships each
 * frame's stdout/stderr to Loki tagged with a `frame_id` label and a
 * `session_start_time` label (one value per attempt/retry of the frame).
 *
 * A single Loki query returns at most `LOKI_QUERY_LIMIT` lines; this is the
 * Loki HTTP API maximum per `query_range` call.
 */

// Maximum number of log lines Loki returns per query_range request.
const LOKI_QUERY_LIMIT = 5000;

// Label RQD attaches to every log stream, holding the unix timestamp of the
// frame attempt that produced the lines. Each distinct value is one "log
// version" in the UI (CueGUI parity).
const SESSION_LABEL = "session_start_time";

/** Shape of a Loki `query_range` stream entry. */
interface LokiStream {
  stream: Record<string, string>;
  // Each value is a [unixNanoTimestamp, logLine] tuple.
  values: [string, string][];
}

interface LokiQueryResponse {
  status: string;
  data?: {
    resultType?: string;
    result?: LokiStream[];
  };
}

interface LokiLabelResponse {
  status: string;
  data?: string[];
}

/** A single log version (frame attempt) available in Loki. */
export interface LokiLogVersion {
  // Raw `session_start_time` label value (unix seconds, possibly fractional).
  sessionStartTime: string;
  // Human-readable label for the dropdown, e.g. "2026-06-17 14:32:05".
  label: string;
}

/**
 * Returns the configured Loki base URL, or an empty string when unset.
 * Trailing slashes are trimmed so callers can append `/loki/api/...` safely.
 */
export function getLokiUrl(): string {
  return (process.env.NEXT_PUBLIC_LOKI_URL || "").trim().replace(/\/+$/, "");
}

/**
 * Whether the Loki backend is configured. When false, callers fall back to
 * the file-based log viewer.
 */
export function isLokiEnabled(): boolean {
  return getLokiUrl().length > 0;
}

// Loki timestamps are unix nanoseconds. Frame/job times in CueWeb are unix
// seconds (often fractional), so scale up. A `null`/`undefined`/`<= 0` time
// means "unknown", in which case we omit the bound and let Loki use its
// default range.
function toUnixNano(unixSeconds?: number): string | undefined {
  if (!unixSeconds || unixSeconds <= 0) return undefined;
  return Math.floor(unixSeconds * 1e9).toString();
}

function unixSecondsToDateString(unixSeconds: number): string {
  const d = new Date(unixSeconds * 1000);
  if (Number.isNaN(d.getTime())) return String(unixSeconds);
  // YYYY-MM-DD HH:MM:SS in local time (matches CueGUI's _unix_to_datetime).
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  );
}

async function lokiGet<T>(pathAndQuery: string): Promise<T> {
  const base = getLokiUrl();
  if (!base) {
    throw new Error("Loki is not configured (NEXT_PUBLIC_LOKI_URL is unset)");
  }
  const res = await fetch(`${base}${pathAndQuery}`, {
    headers: { Accept: "application/json" },
    // Logs change as a frame runs; never serve a stale cached response.
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Loki request failed (${res.status}): ${pathAndQuery}`);
  }
  return (await res.json()) as T;
}

/**
 * Lists the log versions (frame attempts) available in Loki for a frame,
 * newest first. Mirrors `LokiViewPlugin._display_frame_log`: it reads the
 * distinct `session_start_time` label values for the frame.
 *
 * @param frameId   Frame id (the `frame_id` Loki label).
 * @param startTime Lower time bound in unix seconds (use the job start time)
 *                  to narrow the label query; optional.
 */
export async function getFrameLogVersions(
  frameId: string,
  startTime?: number,
): Promise<LokiLogVersion[]> {
  if (!frameId) return [];
  const params = new URLSearchParams({
    query: `{frame_id=${JSON.stringify(frameId)}}`,
  });
  const start = toUnixNano(startTime);
  if (start) params.set("start", start);

  const json = await lokiGet<LokiLabelResponse>(
    `/loki/api/v1/label/${SESSION_LABEL}/values?${params.toString()}`,
  );
  const values = json.data ?? [];

  return values
    // Newest attempt first (numeric sort on the unix timestamp).
    .sort((a, b) => parseFloat(b) - parseFloat(a))
    .map((sessionStartTime) => ({
      sessionStartTime,
      label: unixSecondsToDateString(Math.floor(parseFloat(sessionStartTime))),
    }));
}

/**
 * Fetches the log lines for a frame from Loki, joined by newline.
 *
 * Mirrors `LokiViewPlugin._selectLog`: it runs a forward `query_range` for the
 * `{session_start_time, frame_id}` stream and concatenates the line values.
 *
 * @param frameId          Frame id (the `frame_id` Loki label).
 * @param sessionStartTime Specific attempt to load. When omitted, all attempts
 *                         for the frame are queried.
 * @param startTime        Lower time bound in unix seconds; defaults to the
 *                         session start time when available.
 */
export async function getFrameLogLines(
  frameId: string,
  sessionStartTime?: string,
  startTime?: number,
): Promise<string> {
  if (!frameId) return "";

  const selector = sessionStartTime
    ? `{${SESSION_LABEL}=${JSON.stringify(sessionStartTime)}, frame_id=${JSON.stringify(frameId)}}`
    : `{frame_id=${JSON.stringify(frameId)}}`;

  const params = new URLSearchParams({
    query: selector,
    // Query backward so that when a log exceeds LOKI_QUERY_LIMIT we keep the
    // most recent lines (the viewer scrolls to the bottom on load) rather than
    // the oldest. The entries are re-sorted ascending below for display.
    direction: "backward",
    limit: String(LOKI_QUERY_LIMIT),
  });
  // Prefer the explicit start time, otherwise derive it from the selected
  // session so Loki doesn't reject the query for too-wide a range.
  const start =
    toUnixNano(startTime) ??
    (sessionStartTime ? toUnixNano(parseFloat(sessionStartTime)) : undefined);
  if (start) params.set("start", start);

  const json = await lokiGet<LokiQueryResponse>(
    `/loki/api/v1/query_range?${params.toString()}`,
  );

  // Flatten all streams (e.g. stdout/stderr may arrive as separate streams)
  // and sort by Loki's nanosecond timestamp so lines display in chronological
  // order regardless of which stream they came from. The timestamps exceed
  // Number.MAX_SAFE_INTEGER, so compare them as BigInt to avoid precision loss.
  const streams = json.data?.result ?? [];
  const entries = streams.flatMap((stream) =>
    (stream.values ?? []).map(([ts, line]) => ({ ts, line })),
  );
  entries.sort((a, b) => {
    const at = BigInt(a.ts);
    const bt = BigInt(b.ts);
    return at < bt ? -1 : at > bt ? 1 : 0;
  });
  return entries.map((e) => e.line).join("\n");
}
