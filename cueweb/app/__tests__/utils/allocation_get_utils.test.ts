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

import { getAllocations } from '@/app/utils/get_utils';
import { accessGetApi } from '@/app/utils/api_utils';

jest.mock('@/app/utils/api_utils', () => ({
  accessGetApi: jest.fn(),
}));

describe('getAllocations', () => {
  beforeEach(() => jest.clearAllMocks());

  it('posts to /api/allocation/getallocations and returns the array', async () => {
    const allocs = [{ id: 'a1', name: 'local.general', tag: 'general', facility: 'local' }];
    (accessGetApi as jest.Mock).mockResolvedValue(allocs);

    await expect(getAllocations()).resolves.toEqual(allocs);
    expect(accessGetApi).toHaveBeenCalledWith('/api/allocation/getallocations', JSON.stringify({}));
  });

  it('returns [] when the gateway returns a non-array', async () => {
    (accessGetApi as jest.Mock).mockResolvedValue(null);
    await expect(getAllocations()).resolves.toEqual([]);
  });
});
