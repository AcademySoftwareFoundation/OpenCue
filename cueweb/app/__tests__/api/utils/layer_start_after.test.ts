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

import type { Layer } from '@/app/layers/layer-columns';
import { clearLayerStartAfter, setLayerStartAfter } from '@/app/utils/action_utils';
import {
  isLayerDelayed,
  layerRowClassName,
  layerStartAfterSeconds,
} from '@/app/utils/layer_start_after_utils';
import { accessActionApi } from '@/app/utils/api_utils';
import { handleError, toastSuccess } from '@/app/utils/notify_utils';

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

const layerWith = (fields: Partial<Layer>): Layer => ({ id: 'l1', name: 'layer', ...fields } as Layer);

describe('layerStartAfterSeconds', () => {
  // The gateway marshals the proto int64 start_after as a JSON string, so both
  // shapes have to resolve to the same number.
  it('reads the gateway string form', () => {
    expect(layerStartAfterSeconds(layerWith({ startAfter: '1893456000' }))).toBe(1893456000);
  });

  it('reads a numeric form', () => {
    expect(layerStartAfterSeconds(layerWith({ startAfter: 1893456000 }))).toBe(1893456000);
  });

  it('treats a missing / zero / unparsable field as no delay', () => {
    expect(layerStartAfterSeconds(layerWith({}))).toBe(0);
    expect(layerStartAfterSeconds(layerWith({ startAfter: '0' }))).toBe(0);
    expect(layerStartAfterSeconds(layerWith({ startAfter: 'not-a-number' }))).toBe(0);
  });
});

describe('isLayerDelayed / layerRowClassName', () => {
  const future = String(Math.floor(Date.now() / 1000) + 3600);
  const past = String(Math.floor(Date.now() / 1000) - 3600);

  it('tints a layer whose gate is still in the future', () => {
    expect(isLayerDelayed(layerWith({ startAfter: future }))).toBe(true);
    expect(layerRowClassName(layerWith({ startAfter: future }))).toContain('amber');
  });

  it('self-clears once the deadline has passed', () => {
    expect(isLayerDelayed(layerWith({ startAfter: past }))).toBe(false);
    expect(layerRowClassName(layerWith({ startAfter: past }))).toBeUndefined();
  });

  it('leaves an undelayed layer untinted', () => {
    expect(layerRowClassName(layerWith({}))).toBeUndefined();
  });
});

describe('setLayerStartAfter', () => {
  const layer = layerWith({ startAfter: '0' });

  beforeEach(() => jest.clearAllMocks());

  // No username in the payload: the route resolves it from the session, so a
  // caller cannot attribute a delay to someone else.
  it('posts the epoch seconds per layer and no username', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    const ok = await setLayerStartAfter([layer], 1893456000);
    expect(ok).toBe(true);
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/layer/action/setstartafter',
      [JSON.stringify({ layer, start_after: 1893456000 })],
    );
    expect(toastSuccess).toHaveBeenCalledWith('Set start after on 1 layer(s)');
  });

  it('clears with start_after 0 and says so in the toast', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    const ok = await clearLayerStartAfter([layer]);
    expect(ok).toBe(true);
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/layer/action/setstartafter',
      [JSON.stringify({ layer, start_after: 0 })],
    );
    expect(toastSuccess).toHaveBeenCalledWith('Cleared start after on 1 layer(s)');
  });

  it('surfaces a backend rejection without toasting success', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: false, error: 'INVALID_ARGUMENT' });
    const ok = await setLayerStartAfter([layer], 1893456000);
    expect(ok).toBe(false);
    expect(handleError).toHaveBeenCalled();
    expect(toastSuccess).not.toHaveBeenCalled();
  });
});
