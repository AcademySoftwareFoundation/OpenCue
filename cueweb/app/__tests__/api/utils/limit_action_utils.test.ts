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
  createLimit,
  deleteLimit,
  renameLimit,
  setLimitMaxValue,
} from '@/app/utils/action_utils';
import { accessActionApi } from '@/app/utils/api_utils';

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

describe('limit action_utils helpers', () => {
  beforeEach(() => jest.clearAllMocks());

  it('createLimit posts { name, max_value }', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    await expect(createLimit('test1', 0)).resolves.toBe(true);
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/limit/action/create',
      [JSON.stringify({ name: 'test1', max_value: 0 })],
    );
  });

  it('deleteLimit posts { name }', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    await deleteLimit('test1');
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/limit/action/delete',
      [JSON.stringify({ name: 'test1' })],
    );
  });

  it('renameLimit posts { old_name, new_name }', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    await renameLimit('test1', 'test2');
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/limit/action/rename',
      [JSON.stringify({ old_name: 'test1', new_name: 'test2' })],
    );
  });

  it('setLimitMaxValue posts { name, max_value }', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ success: true });
    await setLimitMaxValue('test1', 50);
    expect(accessActionApi).toHaveBeenCalledWith(
      '/api/limit/action/setmaxvalue',
      [JSON.stringify({ name: 'test1', max_value: 50 })],
    );
  });

  it('returns false when the action reports failure', async () => {
    (accessActionApi as jest.Mock).mockResolvedValue({ error: 'boom' });
    await expect(createLimit('test1', 0)).resolves.toBe(false);
  });
});
