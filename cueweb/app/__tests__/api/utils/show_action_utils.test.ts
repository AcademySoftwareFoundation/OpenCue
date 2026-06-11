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
  enableShowBooking,
  enableShowDispatching,
  setShowDefaultMaxCores,
  setShowDefaultMinCores,
  setShowCommentEmail,
  createShowSubscription,
} from '@/app/utils/action_utils';
import { accessActionApi } from '@/app/utils/api_utils';
import type { Show } from '@/app/utils/get_utils';

jest.mock('@/app/utils/api_utils', () => ({
  accessActionApi: jest.fn(),
  accessGetApi: jest.fn(),
}));

jest.mock('@/app/utils/notify_utils', () => ({
  toastSuccess: jest.fn(),
  toastWarning: jest.fn(),
  handleError: jest.fn(),
}));

jest.mock('@/app/utils/get_utils', () => ({
  getJobForLayer: jest.fn(),
  getFrameLogDir: jest.fn(),
}));

const mockShow: Show = { id: 's1', name: 'testing', active: true };

describe('show action_utils helpers', () => {
  beforeEach(() => jest.clearAllMocks());

  it('enableShowBooking posts { show, enabled } and returns success', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    await expect(enableShowBooking(mockShow, true)).resolves.toBe(true);
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/show/action/enablebooking',
      [JSON.stringify({ show: mockShow, enabled: true })],
    );
  });

  it('enableShowDispatching posts { show, enabled }', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    await enableShowDispatching(mockShow, false);
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/show/action/enabledispatching',
      [JSON.stringify({ show: mockShow, enabled: false })],
    );
  });

  it('setShowDefaultMaxCores posts { show, max_cores }', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    await setShowDefaultMaxCores(mockShow, 200);
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/show/action/setdefaultmaxcores',
      [JSON.stringify({ show: mockShow, max_cores: 200 })],
    );
  });

  it('setShowDefaultMinCores posts { show, min_cores }', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    await setShowDefaultMinCores(mockShow, 2);
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/show/action/setdefaultmincores',
      [JSON.stringify({ show: mockShow, min_cores: 2 })],
    );
  });

  it('setShowCommentEmail posts { show, email }', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    await setShowCommentEmail(mockShow, 'a@b.com');
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/show/action/setcommentemail',
      [JSON.stringify({ show: mockShow, email: 'a@b.com' })],
    );
  });

  it('createShowSubscription posts { show, allocation_id, size, burst }', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    await createShowSubscription(mockShow, 'alloc-1', 100, 110);
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/show/action/createsubscription',
      [JSON.stringify({ show: mockShow, allocation_id: 'alloc-1', size: 100, burst: 110 })],
    );
  });

  it('returns false when the action reports failure', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ error: 'boom' });
    await expect(enableShowBooking(mockShow, true)).resolves.toBe(false);
  });
});
