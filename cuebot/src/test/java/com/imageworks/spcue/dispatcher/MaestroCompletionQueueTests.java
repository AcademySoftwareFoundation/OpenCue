
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.dispatcher;

import org.junit.Test;

import static org.junit.Assert.assertEquals;

/**
 * The drain queue takes every completion that reached cuebot: a refusal past the RQD channel's four
 * attempts would lose the report for good, so there is no depth at which the queue says no.
 */
public class MaestroCompletionQueueTests {

    @Test
    public void offerNeverRefuses() {
        MaestroCompletionQueue.drain();
        int n = 200_001;
        for (int i = 0; i < n; i++) {
            MaestroCompletionQueue
                    .offer(new QueuedFrameCompletion(null, null, null, null, null, null, null, 0));
        }
        assertEquals(n, MaestroCompletionQueue.size());
        assertEquals(n, MaestroCompletionQueue.drain().size());
        assertEquals(0, MaestroCompletionQueue.size());
    }

    @Test
    public void oldestAgeIsTheHeadsWait() {
        MaestroCompletionQueue.drain();
        assertEquals(0, MaestroCompletionQueue.oldestAgeMs(System.currentTimeMillis()));

        QueuedFrameCompletion first =
                new QueuedFrameCompletion(null, null, null, null, null, null, null, 0);
        MaestroCompletionQueue.offer(first);
        MaestroCompletionQueue
                .offer(new QueuedFrameCompletion(null, null, null, null, null, null, null, 0));
        // The head sets the age, however young what is behind it.
        assertEquals(5_000, MaestroCompletionQueue.oldestAgeMs(first.enqueuedAtMs + 5_000));
        // A clock that reads earlier than the stamp never goes negative.
        assertEquals(0, MaestroCompletionQueue.oldestAgeMs(first.enqueuedAtMs - 1));

        MaestroCompletionQueue.drain();
        assertEquals(0, MaestroCompletionQueue.oldestAgeMs(System.currentTimeMillis()));
    }
}
