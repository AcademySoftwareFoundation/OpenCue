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
    eatJobsDeadFrames,
    killJobs,
    reparentGroups,
    reparentJobs,
    unpauseJobs
} from '@/app/utils/action_utils';
import { accessActionApi } from '@/app/utils/api_utils';
import { handleError } from '@/app/utils/notify_utils';

// Mock dependencies
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

global.fetch = jest.fn();

describe('action_utils', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    const mockJob = {
        id:"id",state:"FINISHED",name:"name",shot:"shot",show:"show",
        user:"user",group:"group",facility:"facility",os:"os",uid:1,
        priority:1,minCores:1,maxCores:100,logDir:"logdir",isPaused:false,
        hasComment:false,autoEat:false,startTime:1,stopTime:1,
        jobStats:{
            totalLayers:1,totalFrames:5,waitingFrames:5,runningFrames:0,deadFrames:0,
            eatenFrames:0,dependFrames:0,succeededFrames:0,pendingFrames:5,avgFrameSec:0,
            highFrameSec:0,avgCoreSec:0,renderedFrameCount:"0",failedFrameCount:"0",
            remainingCoreSec:"0",totalCoreSec:"0",renderedCoreSec:"0",failedCoreSec:"0",
            maxRss:"0",reservedCores:0,totalGpuSec:"0",renderedGpuSec:"0",failedGpuSec:"0",
            reservedGpus:0,maxGpuMemory:"0"
            },
        minGpus:0,maxGpus:100
    };

    const username = 'testuser';
    const reason = 'testreason';

    // Testing error handling for killJobs
    describe('killJobs', () => {
        it('should handle API errors gracefully', async () => {
            (accessActionApi as jest.Mock).mockRejectedValue(new Error('API Error'));

            await killJobs([mockJob], username, reason);

            expect(accessActionApi).toHaveBeenCalledWith(
                '/api/job/action/kill',
                [JSON.stringify({ job: mockJob, username, reason })]
            );
            expect(handleError).toHaveBeenCalledWith(
                new Error('API Error'),
                `Error performing action for: /api/job/action/kill`
            );
        });

        it('should handle partial API failures', async () => {
            (accessActionApi as jest.Mock).mockResolvedValueOnce({ success: false, error: 'Partial failure' });

            await killJobs([mockJob], username, reason);

            expect(accessActionApi).toHaveBeenCalledWith(
                '/api/job/action/kill',
                [JSON.stringify({ job: mockJob, username, reason })]
            );
            expect(handleError).toHaveBeenCalledWith(
                new Error('Partial failure'),
                `Error performing action for: /api/job/action/kill`
            );
        });

        it('should handle mixed responses', async () => {
            (accessActionApi as jest.Mock).mockRejectedValue(new Error('Failed to kill job'));
            (fetch as jest.Mock)
                .mockResolvedValueOnce({ ok: true, json: jest.fn().mockResolvedValueOnce({success: true})})
                .mockResolvedValueOnce({ ok: false, json: jest.fn().mockResolvedValueOnce({success: false, error: 'Failed to kill job'})});

            await killJobs([mockJob, mockJob], username, reason);

            // expect(toastSuccess).toHaveBeenCalledWith('Killed 1 job(s)');
            expect(handleError).toHaveBeenCalledWith(new Error('Failed to kill job'), `Error performing action for: /api/job/action/kill`);
        });
    });

    // Error handling for eatJobsDeadFrames
    describe('eatJobsDeadFrames', () => {
        it('should handle API errors and trigger handleError', async () => {
            (accessActionApi as jest.Mock).mockRejectedValue(new Error('API Error'));

            await eatJobsDeadFrames([mockJob]);

            expect(accessActionApi).toHaveBeenCalledWith(
                '/api/job/action/eatframes',
                [JSON.stringify({ job: mockJob, req: { states: { frame_states: [5] } } })]
            );
            expect(handleError).toHaveBeenCalledWith(
                new Error('API Error'),
                `Error performing action for: /api/job/action/eatframes`
            );
        });

        it('should call handleError for API partial failure', async () => {
            (accessActionApi as jest.Mock).mockResolvedValueOnce({ success: false, error: 'Partial failure' });

            await eatJobsDeadFrames([mockJob]);

            expect(handleError).toHaveBeenCalledWith(
                new Error('Partial failure'),
                `Error performing action for: /api/job/action/eatframes`
            );
        });
    });

    // Reparent groups under a new parent group
    describe('reparentGroups', () => {
        it('posts a single ReparentGroups request with the new parent and group ids', async () => {
            (accessActionApi as jest.Mock).mockResolvedValue({ success: true });

            await reparentGroups('parent-1', ['g1', 'g2']);

            expect(accessActionApi).toHaveBeenCalledWith(
                '/api/group/action/reparentgroups',
                [JSON.stringify({
                    group: { id: 'parent-1' },
                    groups: { groups: [{ id: 'g1' }, { id: 'g2' }] },
                })]
            );
        });

        it('returns the result on success (the group tree relies on this to refetch)', async () => {
            (accessActionApi as jest.Mock).mockResolvedValue({ success: true });

            const result = await reparentGroups('parent-1', ['g1']);

            expect(result).toEqual({ success: true });
        });

        it('handles API errors gracefully', async () => {
            (accessActionApi as jest.Mock).mockRejectedValue(new Error('API Error'));

            await reparentGroups('parent-1', ['g1']);

            expect(handleError).toHaveBeenCalledWith(
                new Error('API Error'),
                `Error performing action for: /api/group/action/reparentgroups`
            );
        });

        it('returns an error object on failure (the group tree relies on this to roll back)', async () => {
            (accessActionApi as jest.Mock).mockRejectedValue(new Error('API Error'));

            const result = await reparentGroups('parent-1', ['g1']);

            expect(result).toEqual({ error: 'API Error' });
        });
    });

    // Reparent jobs under a new parent group
    describe('reparentJobs', () => {
        it('posts a single ReparentJobs request with the new parent and job ids', async () => {
            (accessActionApi as jest.Mock).mockResolvedValue({ success: true });

            await reparentJobs('parent-1', ['j1', 'j2']);

            expect(accessActionApi).toHaveBeenCalledWith(
                '/api/group/action/reparentjobs',
                [JSON.stringify({
                    group: { id: 'parent-1' },
                    jobs: { jobs: [{ id: 'j1' }, { id: 'j2' }] },
                })]
            );
        });

        it('returns the result on success (the group tree relies on this to refetch)', async () => {
            (accessActionApi as jest.Mock).mockResolvedValue({ success: true });

            const result = await reparentJobs('parent-1', ['j1']);

            expect(result).toEqual({ success: true });
        });

        it('handles API errors gracefully', async () => {
            (accessActionApi as jest.Mock).mockRejectedValue(new Error('API Error'));

            await reparentJobs('parent-1', ['j1']);

            expect(handleError).toHaveBeenCalledWith(
                new Error('API Error'),
                `Error performing action for: /api/group/action/reparentjobs`
            );
        });

        it('returns an error object on failure (the group tree relies on this to roll back)', async () => {
            (accessActionApi as jest.Mock).mockRejectedValue(new Error('API Error'));

            const result = await reparentJobs('parent-1', ['j1']);

            expect(result).toEqual({ error: 'API Error' });
        });
    });

    // Testing unpauseJobs with error handling
    describe('unpauseJobs', () => {
        it('should handle API errors and trigger handleError', async () => {
            (accessActionApi as jest.Mock).mockRejectedValue(new Error('API Error'));

            await unpauseJobs([mockJob]);

            expect(accessActionApi).toHaveBeenCalledWith(
                '/api/job/action/unpause',
                [JSON.stringify({ job: mockJob })]
            );
            expect(handleError).toHaveBeenCalledWith(
                new Error('API Error'),
                `Error performing action for: /api/job/action/unpause`
            );
        });

        it('should handle partial API failures', async () => {
            (accessActionApi as jest.Mock).mockResolvedValueOnce({ success: false, error: 'Partial failure' });

            await unpauseJobs([mockJob]);

            expect(handleError).toHaveBeenCalledWith(
                new Error('Partial failure'),
                `Error performing action for: /api/job/action/unpause`
            );
        });
    });
});
