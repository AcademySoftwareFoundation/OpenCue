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

import {
  getFrameLogLines,
  getFrameLogVersions,
  getLokiUrl,
  isLokiEnabled,
} from '@/lib/loki';

// The module reads process.env.NEXT_PUBLIC_LOKI_URL at call time (not at
// import time), so each test just sets the env var before exercising the API.
const ORIGINAL_LOKI_URL = process.env.NEXT_PUBLIC_LOKI_URL;

function setLokiUrl(lokiUrl?: string) {
  if (lokiUrl === undefined) {
    delete process.env.NEXT_PUBLIC_LOKI_URL;
  } else {
    process.env.NEXT_PUBLIC_LOKI_URL = lokiUrl;
  }
}

afterEach(() => {
  setLokiUrl(ORIGINAL_LOKI_URL);
  jest.restoreAllMocks();
});

function mockFetch(jsonByUrl: (url: string) => unknown, ok = true, status = 200) {
  const fn = jest.fn(async (url: string) => ({
    ok,
    status,
    json: async () => jsonByUrl(url),
  }));
  // @ts-expect-error - assigning a test double to the global fetch.
  global.fetch = fn;
  return fn;
}

describe('isLokiEnabled / getLokiUrl', () => {
  it('reports disabled when the env var is unset', () => {
    setLokiUrl(undefined);
    expect(isLokiEnabled()).toBe(false);
    expect(getLokiUrl()).toBe('');
  });

  it('reports disabled for a blank/whitespace value', () => {
    setLokiUrl('   ');
    expect(isLokiEnabled()).toBe(false);
  });

  it('reports enabled and strips trailing slashes', () => {
    setLokiUrl('http://loki:3100/');
    expect(isLokiEnabled()).toBe(true);
    expect(getLokiUrl()).toBe('http://loki:3100');
  });
});

describe('getFrameLogVersions', () => {
  it('returns attempts newest-first with human-readable labels', async () => {
    setLokiUrl('http://loki:3100');
    const fetchFn = mockFetch(() => ({
      status: 'success',
      data: ['1700000000', '1700009999', '1700005000'],
    }));

    const versions = await getFrameLogVersions('frame-123', 1699999999);

    // Sorted descending by the unix timestamp.
    expect(versions.map((v) => v.sessionStartTime)).toEqual([
      '1700009999',
      '1700005000',
      '1700000000',
    ]);
    // Each gets a formatted label (not just the raw number).
    expect(versions[0].label).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);

    // Hits the label_values endpoint with a frame_id selector + start bound.
    const calledUrl = fetchFn.mock.calls[0][0] as string;
    expect(calledUrl).toContain('/loki/api/v1/label/session_start_time/values');
    expect(decodeURIComponent(calledUrl)).toContain('{frame_id="frame-123"}');
    expect(calledUrl).toContain('start=1699999999000000000');
  });

  it('returns an empty list when frameId is missing (no fetch)', async () => {
    setLokiUrl('http://loki:3100');
    const fetchFn = mockFetch(() => ({ status: 'success', data: [] }));
    expect(await getFrameLogVersions('')).toEqual([]);
    expect(fetchFn).not.toHaveBeenCalled();
  });
});

describe('getFrameLogLines', () => {
  it('concatenates the line values across streams', async () => {
    setLokiUrl('http://loki:3100');
    const fetchFn = mockFetch(() => ({
      status: 'success',
      data: {
        resultType: 'streams',
        result: [
          {
            stream: { frame_id: 'frame-123' },
            values: [
              ['1700000001000000000', 'line one'],
              ['1700000002000000000', 'line two'],
            ],
          },
        ],
      },
    }));

    const text = await getFrameLogLines('frame-123', '1700000000');

    expect(text).toBe('line one\nline two');
    const calledUrl = fetchFn.mock.calls[0][0] as string;
    expect(calledUrl).toContain('/loki/api/v1/query_range');
    // URLSearchParams form-encodes spaces as '+'; Loki decodes them back.
    expect(decodeURIComponent(calledUrl).replace(/\+/g, ' ')).toContain(
      '{session_start_time="1700000000", frame_id="frame-123"}',
    );
    expect(calledUrl).toContain('direction=backward');
  });

  it('interleaves multiple streams in chronological order', async () => {
    setLokiUrl('http://loki:3100');
    // stdout and stderr arrive as separate streams, out of order relative to
    // each other. Timestamps exceed Number.MAX_SAFE_INTEGER on purpose.
    mockFetch(() => ({
      status: 'success',
      data: {
        resultType: 'streams',
        result: [
          {
            stream: { stream: 'stdout' },
            values: [
              ['1700000001000000000', 'out-1'],
              ['1700000003000000000', 'out-3'],
            ],
          },
          {
            stream: { stream: 'stderr' },
            values: [
              ['1700000002000000000', 'err-2'],
              ['1700000004000000000', 'err-4'],
            ],
          },
        ],
      },
    }));

    const text = await getFrameLogLines('frame-123', '1700000000');
    expect(text).toBe('out-1\nerr-2\nout-3\nerr-4');
  });

  it('returns an empty string when Loki has no streams', async () => {
    setLokiUrl('http://loki:3100');
    mockFetch(() => ({ status: 'success', data: { result: [] } }));
    expect(await getFrameLogLines('frame-123', '1700000000')).toBe('');
  });

  it('throws when the Loki request fails', async () => {
    setLokiUrl('http://loki:3100');
    mockFetch(() => ({}), false, 502);
    await expect(getFrameLogLines('frame-123', '1700000000')).rejects.toThrow(
      /Loki request failed \(502\)/,
    );
  });

  it('throws when Loki is not configured', async () => {
    setLokiUrl(undefined);
    await expect(getFrameLogLines('frame-123')).rejects.toThrow(
      /not configured/,
    );
  });
});
