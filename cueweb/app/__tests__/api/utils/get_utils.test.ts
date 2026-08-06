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
    getShowGroups,
    getGroupJobs,
} from '@/app/utils/get_utils';
import { accessGetApi } from '@/app/utils/api_utils';

jest.mock('@/app/utils/api_utils', () => ({
    accessGetApi: jest.fn(),
}));

jest.mock('@/app/utils/notify_utils', () => ({
    handleError: jest.fn(),
}));

describe('get_utils group helpers', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    const mockGroups = [
        { id: 'g1', name: 'root', parentId: '' },
        { id: 'g2', name: 'sub', parentId: 'g1' },
    ];

    describe('getShowGroups', () => {
        it('posts to /api/show/getgroups with the show id and returns the groups array', async () => {
            (accessGetApi as jest.Mock).mockResolvedValue(mockGroups);

            const result = await getShowGroups('show-123');

            expect(accessGetApi).toHaveBeenCalledWith(
                '/api/show/getgroups',
                JSON.stringify({ show: { id: 'show-123' } })
            );
            expect(result).toEqual(mockGroups);
        });

        it('returns [] when the API responds with null', async () => {
            (accessGetApi as jest.Mock).mockResolvedValue(null);

            const result = await getShowGroups('show-123');

            expect(result).toEqual([]);
        });
    });

    describe('getGroupJobs', () => {
        const mockJobs = [{ id: 'j1', name: 'job-1' }];

        it('posts to /api/group/getjobs with the group id and returns the jobs array', async () => {
            (accessGetApi as jest.Mock).mockResolvedValue(mockJobs);

            const result = await getGroupJobs('group-abc');

            expect(accessGetApi).toHaveBeenCalledWith(
                '/api/group/getjobs',
                JSON.stringify({ group: { id: 'group-abc' } })
            );
            expect(result).toEqual(mockJobs);
        });

        it('returns [] when the API responds with null', async () => {
            (accessGetApi as jest.Mock).mockResolvedValue(null);

            const result = await getGroupJobs('group-abc');

            expect(result).toEqual([]);
        });
    });
});
