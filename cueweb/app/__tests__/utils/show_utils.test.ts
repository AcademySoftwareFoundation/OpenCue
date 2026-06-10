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
  isValidShowName,
  findShow,
  createShow,
  getShows,
  type Show,
} from '@/app/utils/show_utils';
import { accessGetApi } from '@/app/utils/api_utils';

jest.mock('@/app/utils/api_utils', () => ({
  accessGetApi: jest.fn(),
}));

const mockShow: Show = {
  id: 's1', name: 'myshow', active: true, bookingEnabled: true, dispatchEnabled: true,
};

describe('show_utils', () => {
  beforeEach(() => jest.clearAllMocks());

  describe('isValidShowName', () => {
    it('accepts alphanumeric names', () => {
      expect(isValidShowName('myShow123')).toBe(true);
    });
    it('rejects empty, spaces, and punctuation', () => {
      expect(isValidShowName('')).toBe(false);
      expect(isValidShowName('my show')).toBe(false);
      expect(isValidShowName('my-show')).toBe(false);
      expect(isValidShowName('show_1')).toBe(false);
    });
  });

  describe('findShow', () => {
    it('posts the name to /api/show/findshow and returns the show', async () => {
      (accessGetApi as jest.Mock).mockResolvedValue({ show: mockShow });

      await expect(findShow('myshow')).resolves.toEqual(mockShow);
      expect(accessGetApi).toHaveBeenCalledWith(
        '/api/show/findshow',
        JSON.stringify({ name: 'myshow' }),
      );
    });

    it('returns null when the gateway reports the show was not found', async () => {
      (accessGetApi as jest.Mock).mockResolvedValue({ notFound: true });
      await expect(findShow('nope')).resolves.toBeNull();
    });

    it('returns null when nothing comes back', async () => {
      (accessGetApi as jest.Mock).mockResolvedValue(null);
      await expect(findShow('nope')).resolves.toBeNull();
    });
  });

  describe('createShow', () => {
    it('posts the name to /api/show/createshow and returns the created show', async () => {
      (accessGetApi as jest.Mock).mockResolvedValue({ show: mockShow });

      await expect(createShow('myshow')).resolves.toEqual(mockShow);
      expect(accessGetApi).toHaveBeenCalledWith(
        '/api/show/createshow',
        JSON.stringify({ name: 'myshow' }),
      );
    });

    it('throws when creation fails so the form can surface the error', async () => {
      (accessGetApi as jest.Mock).mockResolvedValue(null);
      await expect(createShow('myshow')).rejects.toThrow('Failed to create show');
    });
  });

  describe('getShows', () => {
    it('returns the array of shows', async () => {
      (accessGetApi as jest.Mock).mockResolvedValue([mockShow]);
      await expect(getShows()).resolves.toEqual([mockShow]);
    });

    it('returns [] when the gateway returns a non-array', async () => {
      (accessGetApi as jest.Mock).mockResolvedValue(null);
      await expect(getShows()).resolves.toEqual([]);
    });
  });
});
