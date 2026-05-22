
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

package com.imageworks.spcue.test.service;

import java.util.Arrays;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import io.lettuce.core.RedisNoScriptException;
import io.lettuce.core.api.sync.RedisCommands;
import org.junit.Before;
import org.junit.Test;
import org.springframework.test.util.ReflectionTestUtils;

import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.service.LettuceAccountingRedisPublisher;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Unit tests for {@link LettuceAccountingRedisPublisher}. Uses a Mockito-backed
 * {@code RedisCommands} stub with a custom Answer so we don't have to fight Mockito's vararg
 * matching for the {@code evalsha(String, ScriptOutputType, K[], V...)} signature.
 */
public class LettuceAccountingRedisPublisherTests {

    private static final String SHA = "deadbeef";
    private static final String NEW_SHA = "cafebabe";

    private LettuceAccountingRedisPublisher publisher;
    @SuppressWarnings("unchecked")
    private RedisCommands<String, String> commands = mock(RedisCommands.class);

    private VirtualProc proc;
    private static final String SHOW_ID = "show-uuid";
    private static final String JOB_ID = "job-uuid";
    private static final String LAYER_ID = "layer-uuid";
    private static final String ALLOC_ID = "alloc-uuid";
    private static final String FOLDER_ID = "folder-uuid";
    private static final String DEPT_ID = "dept-uuid";

    /** Captured evalsha invocations across test scenarios. */
    private final AtomicInteger evalshaCount = new AtomicInteger();
    private final AtomicReference<String> lastSha = new AtomicReference<>();
    private final AtomicReference<String[]> lastKeys = new AtomicReference<>();
    private final AtomicReference<String[]> lastArgv = new AtomicReference<>();

    @Before
    public void setUp() {
        publisher = new LettuceAccountingRedisPublisher();
        // Bypass @PostConstruct so we don't dial Redis; manually inject test state.
        ReflectionTestUtils.setField(publisher, "enabled", true);
        ReflectionTestUtils.setField(publisher, "commands", commands);
        ReflectionTestUtils.setField(publisher, "scriptSha", SHA);

        proc = new VirtualProc();
        proc.id = "proc-uuid";
        proc.showId = SHOW_ID;
        proc.jobId = JOB_ID;
        proc.layerId = LAYER_ID;
        proc.allocationId = ALLOC_ID;
        proc.folderId = FOLDER_ID;
        proc.deptId = DEPT_ID;
        // 400 centicores = 4 cores. Cuebot stores cores × 100; the publisher converts to
        // cores on the way to Redis per design §0 unit invariant. 4 != 2 (gpusReserved)
        // keeps the -cores/-gpus argv pair disambiguated in assertions below.
        proc.coresReserved = 400;
        proc.gpusReserved = 2;

        // Mockito's vararg matching is fiddly for evalsha(String, ScriptOutputType, K[], V...).
        // Side-step it with an Answer that records the args; tests can then inspect or
        // overwrite the behavior via setEvalshaBehavior(...).
        evalshaCount.set(0);
        when(commands.evalsha(org.mockito.ArgumentMatchers.anyString(),
                org.mockito.ArgumentMatchers.any(io.lettuce.core.ScriptOutputType.class),
                org.mockito.ArgumentMatchers.any(String[].class),
                org.mockito.ArgumentMatchers.<String>any())).thenAnswer(invocation -> {
                    evalshaCount.incrementAndGet();
                    lastSha.set(invocation.getArgument(0));
                    lastKeys.set(invocation.getArgument(2));
                    Object[] all = invocation.getArguments();
                    String[] argv = new String[all.length - 3];
                    for (int i = 3; i < all.length; i++) {
                        argv[i - 3] = (String) all[i];
                    }
                    lastArgv.set(argv);
                    return 0L;
                });
    }

    /** Replace the evalsha stub with an Answer that always throws the given exception. */
    private void evalshaAlwaysThrows(RuntimeException ex) {
        when(commands.evalsha(org.mockito.ArgumentMatchers.anyString(),
                org.mockito.ArgumentMatchers.any(io.lettuce.core.ScriptOutputType.class),
                org.mockito.ArgumentMatchers.any(String[].class),
                org.mockito.ArgumentMatchers.<String>any())).thenThrow(ex);
    }

    /** Evalsha throws only when the SHA matches the given value; otherwise records as normal. */
    private void evalshaThrowsOnSha(String shaToFail, RuntimeException ex) {
        when(commands.evalsha(org.mockito.ArgumentMatchers.anyString(),
                org.mockito.ArgumentMatchers.any(io.lettuce.core.ScriptOutputType.class),
                org.mockito.ArgumentMatchers.any(String[].class),
                org.mockito.ArgumentMatchers.<String>any())).thenAnswer(invocation -> {
                    String sha = invocation.getArgument(0);
                    if (sha.equals(shaToFail)) {
                        throw ex;
                    }
                    evalshaCount.incrementAndGet();
                    lastSha.set(sha);
                    lastKeys.set(invocation.getArgument(2));
                    Object[] all = invocation.getArguments();
                    String[] argv = new String[all.length - 3];
                    for (int i = 3; i < all.length; i++) {
                        argv[i - 3] = (String) all[i];
                    }
                    lastArgv.set(argv);
                    return 0L;
                });
    }

    @Test
    public void disabledPublisherIsNoop() {
        ReflectionTestUtils.setField(publisher, "enabled", false);
        assertFalse(publisher.isEnabled());

        publisher.publishRelease(proc);

        assertEquals(0, evalshaCount.get());
    }

    @Test
    public void publishReleaseSendsExpectedKeysAndArgs() {
        assertTrue(publisher.isEnabled());

        publisher.publishRelease(proc);

        assertEquals(1, evalshaCount.get());
        assertEquals(SHA, lastSha.get());

        // Validates the schema laid out in SCHED_REDIS_DECISIONS.md §2.3 and pins the
        // alloc_id-not-name decision (the subscription key uses the allocation UUID).
        String[] expectedKeys = new String[] {"acct:sub:" + SHOW_ID + ":" + ALLOC_ID,
                "acct:folder:" + FOLDER_ID, "acct:job:" + JOB_ID, "acct:layer:" + LAYER_ID,
                "acct:point:" + DEPT_ID + ":" + SHOW_ID, "acct:seq"};
        assertArrayEquals(expectedKeys, lastKeys.get());

        // Five pairs of (-cores, -gpus), one per accounting table. Cores are sent in
        // Redis cores (centicores / 100), so 400 -> "-4". GPUs pass through unconverted.
        String[] expectedArgv =
                new String[] {"-4", "-2", "-4", "-2", "-4", "-2", "-4", "-2", "-4", "-2"};
        assertArrayEquals(expectedArgv, lastArgv.get());
    }

    @Test
    public void noScriptExceptionTriggersReloadAndRetry() {
        // First evalsha (with stale SHA) throws; reload returns new SHA; retry succeeds.
        evalshaThrowsOnSha(SHA, new RedisNoScriptException("NOSCRIPT"));
        when(commands.scriptLoad(org.mockito.ArgumentMatchers.anyString())).thenReturn(NEW_SHA);

        publisher.publishRelease(proc);

        // The retry (with NEW_SHA) was recorded by the Answer.
        assertEquals(1, evalshaCount.get());
        assertEquals(NEW_SHA, lastSha.get());
        // scriptSha field updated for subsequent calls.
        assertEquals(NEW_SHA, ReflectionTestUtils.getField(publisher, "scriptSha"));
    }

    @Test
    public void genericExceptionIsSwallowed() {
        evalshaAlwaysThrows(new RuntimeException("redis unreachable"));

        // Should not propagate; recompute heals the missing decrement per §4.3 row 1.
        // Reaching the next line is the assertion.
        publisher.publishRelease(proc);
    }

    /** Sanity check that our test fixture's Lua script-content captor really sees varargs. */
    @Test
    public void varargCaptureSmokeTest() {
        publisher.publishRelease(proc);
        assertEquals(10, lastArgv.get().length);
        // First pair is from acct:sub key — uses -cores then -gpus.
        assertEquals(Arrays.asList("-4", "-2"),
                Arrays.asList(lastArgv.get()[0], lastArgv.get()[1]));
    }
}
