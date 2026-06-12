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

import { editLayerProperties } from '@/app/utils/action_utils';
import { accessActionApi } from '@/app/utils/api_utils';
import { handleError, toastSuccess } from '@/app/utils/notify_utils';
import { parseMemoryToKb, formatKbToGbInput } from '@/app/utils/layers_frames_utils';

jest.mock('@/app/utils/api_utils', () => ({
  accessActionApi: jest.fn(),
}));
jest.mock('@/app/utils/notify_utils', () => ({
  toastSuccess: jest.fn(),
  toastWarning: jest.fn(),
  handleError: jest.fn(),
}));
jest.mock('@/app/utils/get_utils', () => ({
  getJobForLayer: jest.fn(),
}));

const mockLayer: any = {
  id: 'layer-id',
  name: 'layer-name',
  minCores: 1,
  minMemory: '4194304', // 4 GB in KB
  tags: ['general'],
};

describe('editLayerProperties', () => {
  beforeEach(() => jest.clearAllMocks());

  it('POSTs only the changed fields and toasts once on success', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    const ok = await editLayerProperties(mockLayer, {
      minMemory: 8388608,
      minCores: 2,
      tags: ['general', 'desktop'],
    });
    expect(ok).toBe(true);
    expect(accessActionApi).toHaveBeenNthCalledWith(
      1, '/api/layer/action/setminmemory', [JSON.stringify({ layer: mockLayer, memory: 8388608 })],
    );
    expect(accessActionApi).toHaveBeenNthCalledWith(
      2, '/api/layer/action/setmincores', [JSON.stringify({ layer: mockLayer, cores: 2 })],
    );
    expect(accessActionApi).toHaveBeenNthCalledWith(
      3, '/api/layer/action/settags', [JSON.stringify({ layer: mockLayer, tags: ['general', 'desktop'] })],
    );
    expect(toastSuccess).toHaveBeenCalledTimes(1);
  });

  it('skips fields not present in the change set', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    const ok = await editLayerProperties(mockLayer, { minCores: 4 });
    expect(ok).toBe(true);
    expect(accessActionApi).toHaveBeenCalledTimes(1);
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/layer/action/setmincores', [JSON.stringify({ layer: mockLayer, cores: 4 })],
    );
  });

  it('sends a zero-core change (typeof number guard, not truthiness)', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    const ok = await editLayerProperties(mockLayer, { minCores: 0 });
    expect(ok).toBe(true);
    expect(accessActionApi).toHaveBeenCalledTimes(1);
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/layer/action/setmincores', [JSON.stringify({ layer: mockLayer, cores: 0 })],
    );
  });

  it('stops after the first failing call and surfaces the error without toasting', async () => {
    (accessActionApi as jest.Mock).mockResolvedValueOnce({ success: false, error: 'boom' });
    const ok = await editLayerProperties(mockLayer, { minMemory: 8388608, minCores: 2 });
    expect(ok).toBe(false);
    expect(accessActionApi).toHaveBeenCalledTimes(1);
    expect(handleError).toHaveBeenCalled();
    expect(toastSuccess).not.toHaveBeenCalled();
  });
});

describe('parseMemoryToKb', () => {
  it('treats a bare number as GB (CueGUI parity)', () => {
    expect(parseMemoryToKb('4')).toBe(4 * 1024 * 1024);
    expect(parseMemoryToKb('2.5')).toBe(Math.round(2.5 * 1024 * 1024));
  });

  it('honours K/M/G/T unit suffixes case-insensitively', () => {
    expect(parseMemoryToKb('512K')).toBe(512);
    expect(parseMemoryToKb('512kb')).toBe(512);
    expect(parseMemoryToKb('512M')).toBe(512 * 1024);
    expect(parseMemoryToKb('4GB')).toBe(4 * 1024 * 1024);
    expect(parseMemoryToKb('1t')).toBe(1024 * 1024 * 1024);
  });

  it('tolerates whitespace between the number and unit', () => {
    expect(parseMemoryToKb('  2 GB ')).toBe(2 * 1024 * 1024);
  });

  it('rejects blank, non-numeric, non-positive and unknown-unit input', () => {
    expect(parseMemoryToKb('')).toBeNull();
    expect(parseMemoryToKb('   ')).toBeNull();
    expect(parseMemoryToKb('abc')).toBeNull();
    expect(parseMemoryToKb('0')).toBeNull();
    expect(parseMemoryToKb('-4')).toBeNull();
    expect(parseMemoryToKb('4PB')).toBeNull();
    expect(parseMemoryToKb('4 GB extra')).toBeNull();
  });
});

describe('formatKbToGbInput', () => {
  it('formats KB as a trimmed GB string', () => {
    expect(formatKbToGbInput(4 * 1024 * 1024)).toBe('4');
    expect(formatKbToGbInput(Math.round(2.5 * 1024 * 1024))).toBe('2.5');
  });

  it('round-trips with parseMemoryToKb for whole-GB values', () => {
    const kb = 8 * 1024 * 1024;
    expect(parseMemoryToKb(formatKbToGbInput(kb))).toBe(kb);
  });

  it('returns an empty string for non-positive or non-finite input', () => {
    expect(formatKbToGbInput(0)).toBe('');
    expect(formatKbToGbInput(-1)).toBe('');
    expect(formatKbToGbInput(Number.NaN)).toBe('');
  });
});
