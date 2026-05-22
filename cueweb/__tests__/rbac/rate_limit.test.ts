/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  _resetRateLimitStore,
  isBlocked,
  recordFailedAttempt,
} from "@/lib/rbac/rate_limit";

beforeEach(() => {
  _resetRateLimitStore();
});

describe("rate_limit", () => {
  test("blocks after 5 failed attempts in 15 minutes", () => {
    const key = "local:1.2.3.4";
    expect(isBlocked(key).blocked).toBe(false);
    for (let i = 0; i < 4; i++) {
      const r = recordFailedAttempt(key);
      expect(r.blocked).toBe(false);
    }
    const fifth = recordFailedAttempt(key);
    expect(fifth.blocked).toBe(true);
    expect(fifth.retryInMs).toBeGreaterThan(0);
    expect(isBlocked(key).blocked).toBe(true);
  });

  test("separate keys are tracked independently", () => {
    for (let i = 0; i < 5; i++) recordFailedAttempt("local:1.1.1.1");
    expect(isBlocked("local:1.1.1.1").blocked).toBe(true);
    expect(isBlocked("local:2.2.2.2").blocked).toBe(false);
  });
});
