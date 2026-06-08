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
  findHostByName,
  getHostProcs,
  getHostComments,
  type Host,
} from '@/app/utils/get_utils';
import { accessGetApi } from '@/app/utils/api_utils';

jest.mock('@/app/utils/api_utils', () => ({
  accessGetApi: jest.fn(),
}));

const mockHost: Host = {
  id: 'h1', name: 'rqd-01', state: 'UP', lockState: 'OPEN', nimbyEnabled: false,
  cores: 8, idleCores: 8, memory: '0', idleMemory: '0', totalMemory: '0',
  freeMcp: '0', bootTime: 0, pingTime: 0,
};

describe('host get_utils helpers', () => {
  beforeEach(() => jest.clearAllMocks());

  describe('findHostByName', () => {
    it('posts the name to /api/host/findhost and returns the host', async () => {
      (accessGetApi as jest.Mock).mockResolvedValue(mockHost);

      const result = await findHostByName('rqd-01');

      expect(accessGetApi).toHaveBeenCalledWith(
        '/api/host/findhost',
        JSON.stringify({ name: 'rqd-01' }),
      );
      expect(result).toEqual(mockHost);
    });

    it('returns null when no host matches', async () => {
      (accessGetApi as jest.Mock).mockResolvedValue(null);
      await expect(findHostByName('nope')).resolves.toBeNull();
    });
  });

  describe('getHostProcs', () => {
    it('posts the host to /api/host/getprocs and returns the array', async () => {
      const procs = [{ id: 'p1', jobName: 'job', frameName: '0001-comp' }];
      (accessGetApi as jest.Mock).mockResolvedValue(procs);

      const result = await getHostProcs(mockHost);

      expect(accessGetApi).toHaveBeenCalledWith(
        '/api/host/getprocs',
        JSON.stringify({ host: mockHost }),
      );
      expect(result).toEqual(procs);
    });

    it('returns [] when the gateway returns a non-array', async () => {
      (accessGetApi as jest.Mock).mockResolvedValue(null);
      await expect(getHostProcs(mockHost)).resolves.toEqual([]);
    });
  });

  describe('getHostComments', () => {
    it('posts the host to /api/host/getcomments and returns the array', async () => {
      const comments = [{ id: 'c1', timestamp: 1, user: 'u', subject: 's', message: 'm' }];
      (accessGetApi as jest.Mock).mockResolvedValue(comments);

      const result = await getHostComments(mockHost);

      expect(accessGetApi).toHaveBeenCalledWith(
        '/api/host/getcomments',
        JSON.stringify({ host: mockHost }),
      );
      expect(result).toEqual(comments);
    });

    it('returns [] when the gateway returns a non-array', async () => {
      (accessGetApi as jest.Mock).mockResolvedValue(undefined);
      await expect(getHostComments(mockHost)).resolves.toEqual([]);
    });
  });
});
