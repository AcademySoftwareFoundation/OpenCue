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

import { setJobCores } from '@/app/utils/action_utils';
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

const mockJob: any = { id: 'id', name: 'name', state: 'IN_PROGRESS', minCores: 1, maxCores: 8 };

describe('setJobCores', () => {
  beforeEach(() => jest.clearAllMocks());

  it('sends setmincores then setmaxcores and toasts once on success', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    const ok = await setJobCores(mockJob, 2, 8);
    expect(ok).toBe(true);
    expect(accessActionApi).toHaveBeenNthCalledWith(
      1, '/api/job/action/setmincores', [JSON.stringify({ job: mockJob, val: 2 })],
    );
    expect(accessActionApi).toHaveBeenNthCalledWith(
      2, '/api/job/action/setmaxcores', [JSON.stringify({ job: mockJob, val: 8 })],
    );
    expect(toastSuccess).toHaveBeenCalledTimes(1);
  });

  it('stops after min fails and surfaces the error', async () => {
    (accessActionApi as jest.Mock).mockResolvedValueOnce({ success: false, error: 'boom' });
    const ok = await setJobCores(mockJob, 2, 8);
    expect(ok).toBe(false);
    expect(accessActionApi).toHaveBeenCalledTimes(1);
    expect(handleError).toHaveBeenCalled();
    expect(toastSuccess).not.toHaveBeenCalled();
  });

  it('stops after max fails and surfaces the error without toasting', async () => {
    (accessActionApi as jest.Mock)
      .mockResolvedValueOnce({ success: true })
      .mockResolvedValueOnce({ success: false, error: 'max boom' });
    const ok = await setJobCores(mockJob, 2, 8);
    expect(ok).toBe(false);
    expect(accessActionApi).toHaveBeenCalledTimes(2);
    expect(handleError).toHaveBeenCalled();
    expect(toastSuccess).not.toHaveBeenCalled();
  });
});
