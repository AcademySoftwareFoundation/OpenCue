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

import { unbookJob } from '@/app/utils/action_utils';
import { accessActionApi } from '@/app/utils/api_utils';

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

const mockJob: any = { id: 'id', name: 'jobname', state: 'IN_PROGRESS' };

describe('unbookJob', () => {
  beforeEach(() => jest.clearAllMocks());

  it('posts job-scoped criteria with kill=false', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    const ok = await unbookJob(mockJob, false);
    expect(ok).toBe(true);
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/proc/action/unbook',
      [JSON.stringify({ r: { jobs: ['jobname'] }, kill: false })],
    );
  });

  it('passes kill=true through', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    const ok = await unbookJob(mockJob, true);
    expect(ok).toBe(true);
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/proc/action/unbook',
      [JSON.stringify({ r: { jobs: ['jobname'] }, kill: true })],
    );
  });

  it('returns false when the action fails', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: false, error: 'boom' });
    const ok = await unbookJob(mockJob, false);
    expect(ok).toBe(false);
  });
});
