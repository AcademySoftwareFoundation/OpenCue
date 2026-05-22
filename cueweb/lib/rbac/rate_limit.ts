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

import "server-only";

/**
 * Process-local sliding-window rate limiter. Used to throttle failed
 * /login/local attempts. In-memory only; multi-replica deployments
 * should run an external limiter (Redis, NGINX, etc.) in front of
 * CueWeb instead.
 */

type Window = { hits: number; resetAt: number };

const WINDOW_MS = 15 * 60 * 1000;
const MAX_HITS = 5;

const store = new Map<string, Window>();

// Iterate the store and drop any window whose reset time has passed.
// Without this sweep, a broad username/IP spray would leave one entry
// per attempted key in memory forever, since entries are normally only
// touched again when the same IP retries.
function pruneExpired(now: number): void {
  // Array.from snapshots the entries so we can safely delete while
  // iterating, and avoids relying on downlevel iteration of Map.
  for (const [k, w] of Array.from(store.entries())) {
    if (w.resetAt <= now) store.delete(k);
  }
}

export function recordFailedAttempt(key: string): {
  blocked: boolean;
  retryInMs: number;
} {
  const now = Date.now();
  pruneExpired(now);
  const w = store.get(key);
  if (!w || w.resetAt <= now) {
    store.set(key, { hits: 1, resetAt: now + WINDOW_MS });
    return { blocked: false, retryInMs: 0 };
  }
  w.hits += 1;
  if (w.hits >= MAX_HITS) {
    return { blocked: true, retryInMs: w.resetAt - now };
  }
  return { blocked: false, retryInMs: 0 };
}

export function clearAttempts(key: string): void {
  store.delete(key);
}

export function isBlocked(key: string): { blocked: boolean; retryInMs: number } {
  const now = Date.now();
  pruneExpired(now);
  const w = store.get(key);
  if (!w || w.resetAt <= now) return { blocked: false, retryInMs: 0 };
  if (w.hits >= MAX_HITS) return { blocked: true, retryInMs: w.resetAt - now };
  return { blocked: false, retryInMs: 0 };
}

// Test-only.
export function _resetRateLimitStore(): void {
  store.clear();
}
