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
  computeAllocationHostStats,
  buildAllocationRows,
} from '@/app/allocations/allocation-utils';
import type { Allocation, Host } from '@/app/utils/get_utils';

const host = (over: Partial<Host>): Host => ({
  id: 'h', name: 'h', state: 'UP', lockState: 'OPEN', nimbyEnabled: false,
  cores: 0, idleCores: 0, memory: '0', idleMemory: '0', totalMemory: '0',
  freeMcp: '0', bootTime: 0, pingTime: 0, ...over,
});

describe('computeAllocationHostStats', () => {
  it('sums DOWN/REPAIR cores and counts REPAIR hosts per allocation', () => {
    const hosts: Host[] = [
      host({ allocName: 'local.general', state: 'DOWN', cores: 8 }),
      host({ allocName: 'local.general', state: 'REPAIR', cores: 4 }),
      host({ allocName: 'local.general', state: 'REPAIR', cores: 2 }),
      host({ allocName: 'local.general', state: 'UP', cores: 16 }),
      host({ allocName: 'cloud.general', state: 'DOWN', cores: 32 }),
    ];

    const stats = computeAllocationHostStats(hosts);

    expect(stats['local.general']).toEqual({ downCores: 8, repairCores: 6, repairHosts: 2 });
    expect(stats['cloud.general']).toEqual({ downCores: 32, repairCores: 0, repairHosts: 0 });
  });

  it('ignores hosts with no allocName', () => {
    const stats = computeAllocationHostStats([host({ state: 'DOWN', cores: 5 })]);
    expect(stats).toEqual({});
  });

  it('returns {} for no hosts', () => {
    expect(computeAllocationHostStats([])).toEqual({});
  });
});

describe('buildAllocationRows', () => {
  const alloc = (name: string): Allocation => ({
    id: name, name, tag: 'general', facility: 'local',
    stats: {
      cores: 20, availableCores: 10, idleCores: 10, runningCores: 0,
      lockedCores: 0, hosts: 2, lockedHosts: 0, downHosts: 0,
    },
  });

  it('merges derived host stats onto each allocation', () => {
    const rows = buildAllocationRows(
      [alloc('local.general')],
      { 'local.general': { downCores: 8, repairCores: 6, repairHosts: 2 } },
    );
    expect(rows[0].name).toBe('local.general');
    expect(rows[0].stats?.cores).toBe(20);
    expect(rows[0].downCores).toBe(8);
    expect(rows[0].repairCores).toBe(6);
    expect(rows[0].repairHosts).toBe(2);
  });

  it('defaults derived stats to 0 when an allocation has no matching hosts', () => {
    const rows = buildAllocationRows([alloc('cloud.unassigned')], {});
    expect(rows[0].downCores).toBe(0);
    expect(rows[0].repairCores).toBe(0);
    expect(rows[0].repairHosts).toBe(0);
  });
});
