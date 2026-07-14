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
    lockHosts,
    unlockHosts,
    rebootHosts,
    rebootHostsWhenIdle,
    addHostTags,
    removeHostTags,
} from '@/app/utils/action_utils';
import { accessActionApi } from '@/app/utils/api_utils';
import { toastSuccess, handleError } from '@/app/utils/notify_utils';
import type { Host } from '@/app/utils/get_utils';

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
    getFrameLogDir: jest.fn(),
}));

describe('host action_utils', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    const mockHost: Host = {
        id: 'host-id', name: 'rqd-host-01', state: 'UP', lockState: 'OPEN',
        nimbyEnabled: false, cores: 8, idleCores: 8, memory: '0',
        idleMemory: '0', totalMemory: '0', freeMcp: '0', bootTime: 0, pingTime: 0,
    };
    const mockHost2: Host = { ...mockHost, id: 'host-id-2', name: 'rqd-host-02' };

    describe('lockHosts', () => {
        it('posts one body per host to the lock endpoint and toasts success', async () => {
            (accessActionApi as jest.Mock).mockResolvedValue({ success: true });

            await lockHosts([mockHost, mockHost2]);

            expect(accessActionApi).toHaveBeenCalledWith(
                '/api/host/action/lock',
                [
                    JSON.stringify({ host: mockHost }),
                    JSON.stringify({ host: mockHost2 }),
                ],
            );
            expect(toastSuccess).toHaveBeenCalledWith('Locked 2 host(s)');
            expect(handleError).not.toHaveBeenCalled();
        });

        it('routes API errors through handleError', async () => {
            (accessActionApi as jest.Mock).mockRejectedValue(new Error('API Error'));

            await lockHosts([mockHost]);

            expect(accessActionApi).toHaveBeenCalledWith(
                '/api/host/action/lock',
                [JSON.stringify({ host: mockHost })],
            );
            expect(handleError).toHaveBeenCalledWith(
                new Error('API Error'),
                'Error performing action for: /api/host/action/lock',
            );
        });

        it('routes partial failures through handleError', async () => {
            (accessActionApi as jest.Mock).mockResolvedValueOnce({ success: false, error: 'Partial failure' });

            await lockHosts([mockHost]);

            expect(handleError).toHaveBeenCalledWith(
                new Error('Partial failure'),
                'Error performing action for: /api/host/action/lock',
            );
        });

        it('does nothing when called with no hosts', async () => {
            await lockHosts([]);
            expect(accessActionApi).not.toHaveBeenCalled();
            expect(toastSuccess).not.toHaveBeenCalled();
        });
    });

    describe('unlockHosts', () => {
        it('posts one body per host to the unlock endpoint and toasts success', async () => {
            (accessActionApi as jest.Mock).mockResolvedValue({ success: true });

            await unlockHosts([mockHost]);

            expect(accessActionApi).toHaveBeenCalledWith(
                '/api/host/action/unlock',
                [JSON.stringify({ host: mockHost })],
            );
            expect(toastSuccess).toHaveBeenCalledWith('Unlocked 1 host(s)');
        });

        it('routes API errors through handleError', async () => {
            (accessActionApi as jest.Mock).mockRejectedValue(new Error('API Error'));

            await unlockHosts([mockHost]);

            expect(handleError).toHaveBeenCalledWith(
                new Error('API Error'),
                'Error performing action for: /api/host/action/unlock',
            );
        });
    });

    describe('rebootHosts', () => {
        it('posts one body per host to the reboot endpoint and toasts success', async () => {
            (accessActionApi as jest.Mock).mockResolvedValue({ success: true });

            await rebootHosts([mockHost, mockHost2]);

            expect(accessActionApi).toHaveBeenCalledWith(
                '/api/host/action/reboot',
                [
                    JSON.stringify({ host: mockHost }),
                    JSON.stringify({ host: mockHost2 }),
                ],
            );
            expect(toastSuccess).toHaveBeenCalledWith('Rebooting 2 host(s)');
            expect(handleError).not.toHaveBeenCalled();
        });

        it('routes API errors through handleError', async () => {
            (accessActionApi as jest.Mock).mockRejectedValue(new Error('API Error'));

            await rebootHosts([mockHost]);

            expect(handleError).toHaveBeenCalledWith(
                new Error('API Error'),
                'Error performing action for: /api/host/action/reboot',
            );
        });
    });

    describe('rebootHostsWhenIdle', () => {
        it('posts one body per host to the rebootwhenidle endpoint and toasts success', async () => {
            (accessActionApi as jest.Mock).mockResolvedValue({ success: true });

            await rebootHostsWhenIdle([mockHost]);

            expect(accessActionApi).toHaveBeenCalledWith(
                '/api/host/action/rebootwhenidle',
                [JSON.stringify({ host: mockHost })],
            );
            expect(toastSuccess).toHaveBeenCalledWith('Scheduled reboot-when-idle for 1 host(s)');
        });

        it('routes API errors through handleError', async () => {
            (accessActionApi as jest.Mock).mockRejectedValue(new Error('API Error'));

            await rebootHostsWhenIdle([mockHost]);

            expect(handleError).toHaveBeenCalledWith(
                new Error('API Error'),
                'Error performing action for: /api/host/action/rebootwhenidle',
            );
        });
    });

    describe('addHostTags', () => {
        it('posts { host, tags } to the addtags endpoint and toasts success', async () => {
            (accessActionApi as jest.Mock).mockResolvedValue({ success: true });

            await addHostTags([mockHost], ['general', 'gpu']);

            expect(accessActionApi).toHaveBeenCalledWith(
                '/api/host/action/addtags',
                [JSON.stringify({ host: mockHost, tags: ['general', 'gpu'] })],
            );
            expect(toastSuccess).toHaveBeenCalledWith('Added 2 tag(s) to 1 host(s)');
        });

        it('is a no-op when there are no tags to add', async () => {
            await addHostTags([mockHost], []);
            expect(accessActionApi).not.toHaveBeenCalled();
            expect(toastSuccess).not.toHaveBeenCalled();
        });

        it('routes API errors through handleError', async () => {
            (accessActionApi as jest.Mock).mockRejectedValue(new Error('API Error'));

            await addHostTags([mockHost], ['gpu']);

            expect(handleError).toHaveBeenCalledWith(
                new Error('API Error'),
                'Error performing action for: /api/host/action/addtags',
            );
        });
    });

    describe('removeHostTags', () => {
        it('posts { host, tags } to the removetags endpoint and toasts success', async () => {
            (accessActionApi as jest.Mock).mockResolvedValue({ success: true });

            await removeHostTags([mockHost, mockHost2], ['old']);

            expect(accessActionApi).toHaveBeenCalledWith(
                '/api/host/action/removetags',
                [
                    JSON.stringify({ host: mockHost, tags: ['old'] }),
                    JSON.stringify({ host: mockHost2, tags: ['old'] }),
                ],
            );
            expect(toastSuccess).toHaveBeenCalledWith('Removed 1 tag(s) from 2 host(s)');
        });

        it('is a no-op when there are no tags to remove', async () => {
            await removeHostTags([mockHost], []);
            expect(accessActionApi).not.toHaveBeenCalled();
        });
    });
});
