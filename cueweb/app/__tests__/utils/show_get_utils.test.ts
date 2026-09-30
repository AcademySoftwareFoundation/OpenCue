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

import { getActiveShows, getAllocations } from '@/app/utils/get_utils';
import { accessGetApi } from '@/app/utils/api_utils';

jest.mock('@/app/utils/api_utils', () => ({
  accessGetApi: jest.fn(),
}));

describe('show/allocation get_utils helpers', () => {
  beforeEach(() => jest.clearAllMocks());

  describe('getActiveShows', () => {
    it('posts to /api/show/getactiveshows and returns the array', async () => {
      const shows = [{ id: 's1', name: 'testing', active: true }];
      (accessGetApi as jest.Mock).mockResolvedValue(shows);

      await expect(getActiveShows()).resolves.toEqual(shows);
      expect(accessGetApi).toHaveBeenCalledWith('/api/show/getactiveshows', JSON.stringify({}));
    });

    it('returns [] when the gateway returns a non-array', async () => {
      (accessGetApi as jest.Mock).mockResolvedValue(null);
      await expect(getActiveShows()).resolves.toEqual([]);
    });
  });

  describe('getAllocations', () => {
    it('posts to /api/allocation/getall and returns the array', async () => {
      const allocs = [{ id: 'a1', name: 'cloud.general' }];
      (accessGetApi as jest.Mock).mockResolvedValue(allocs);

      await expect(getAllocations()).resolves.toEqual(allocs);
      expect(accessGetApi).toHaveBeenCalledWith('/api/allocation/getall', JSON.stringify({}));
    });

    it('returns [] when the gateway returns a non-array', async () => {
      (accessGetApi as jest.Mock).mockResolvedValue(undefined);
      await expect(getAllocations()).resolves.toEqual([]);
    });
  });
});
