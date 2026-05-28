
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

package com.imageworks.spcue.service;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;

import io.lettuce.core.RedisClient;
import io.lettuce.core.RedisNoScriptException;
import io.lettuce.core.RedisURI;
import io.lettuce.core.ScriptOutputType;
import io.lettuce.core.api.StatefulRedisConnection;
import io.lettuce.core.api.sync.RedisCommands;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;

import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.ShowDao;

/**
 * Lettuce-backed implementation of {@link AccountingRedisPublisher}. Gated by the
 * {@code accounting.redis.enabled} property; when false this class loads but {@link #initialize()}
 * skips connection setup and {@link #publishRelease} short-circuits.
 *
 * <p>
 * Atomicity: each release applies five HINCRBY decrements and an INCR on {@code acct:seq} in a
 * single Lua script. The sequence guard is required by the reseed protocol (see the "acct:seq
 * sequence-number guard" section of the Redis-Backed Accounting Reference at
 * {@code docs/_docs/developer-guide/redis-accounting.md}); without it, a reseed running
 * concurrently with a release would silently clobber the decrement.
 *
 * <p>
 * Failure mode: a publish failure leaves Redis missing a decrement, which the Rust scheduler's
 * few-minutes recompute heals from {@code SUM(proc)} (see "Failure modes and drift bounds" in the
 * same reference). We therefore swallow exceptions with a WARN log rather than letting them
 * propagate back into the (already-committed) caller.
 */
public class LettuceAccountingRedisPublisher implements AccountingRedisPublisher {

    private static final Logger logger =
            LogManager.getLogger(LettuceAccountingRedisPublisher.class);

    /**
     * Redis key layout.
     *
     * <pre>
     * KEYS[1] = acct:sub:{show_id}:{alloc_id}    ARGV[1] = -cores  ARGV[2]  = -gpus
     * KEYS[2] = acct:folder:{folder_id}          ARGV[3] = -cores  ARGV[4]  = -gpus
     * KEYS[3] = acct:job:{job_id}                ARGV[5] = -cores  ARGV[6]  = -gpus
     * KEYS[4] = acct:layer:{layer_id}            ARGV[7] = -cores  ARGV[8]  = -gpus
     * KEYS[5] = acct:point:{dept_id}:{show_id}   ARGV[9] = -cores  ARGV[10] = -gpus
     * KEYS[6] = acct:seq
     * </pre>
     */
    static final String RELEASE_LUA = "redis.call('HINCRBY', KEYS[1], 'int_cores', ARGV[1]); "
            + "redis.call('HINCRBY', KEYS[1], 'int_gpus',  ARGV[2]); "
            + "redis.call('HINCRBY', KEYS[2], 'int_cores', ARGV[3]); "
            + "redis.call('HINCRBY', KEYS[2], 'int_gpus',  ARGV[4]); "
            + "redis.call('HINCRBY', KEYS[3], 'int_cores', ARGV[5]); "
            + "redis.call('HINCRBY', KEYS[3], 'int_gpus',  ARGV[6]); "
            + "redis.call('HINCRBY', KEYS[4], 'int_cores', ARGV[7]); "
            + "redis.call('HINCRBY', KEYS[4], 'int_gpus',  ARGV[8]); "
            + "redis.call('HINCRBY', KEYS[5], 'int_cores', ARGV[9]); "
            + "redis.call('HINCRBY', KEYS[5], 'int_gpus',  ARGV[10]); "
            + "return redis.call('INCR', KEYS[6]);";

    @Autowired
    private Environment env;

    @Autowired
    private ShowDao showDao;

    private RedisClient client;
    private StatefulRedisConnection<String, String> connection;
    private RedisCommands<String, String> commands;
    private volatile String scriptSha;
    private volatile boolean enabled = false;

    @PostConstruct
    public void initialize() {
        enabled = env.getProperty("accounting.redis.enabled", Boolean.class, false);

        // Deployment invariant (§4.1): scheduler-managed shows exist but publishing is off ->
        // counters drift up monotonically. Loud warning routed through Sentry via log4j2.
        int managedCount = showDao.countSchedulerManagedShows();
        if (managedCount > 0 && !enabled) {
            logger.warn("Scheduler-managed shows exist ({} found) but "
                    + "accounting.redis.enabled=false. Booking releases will not be published to "
                    + "Redis; the standalone scheduler's accounting will silently over-count. Set "
                    + "accounting.redis.enabled=true on every Cuebot, OR run "
                    + "`cueadmin -scheduler-managed <show> off` on each managed show before the "
                    + "scheduler starts.", managedCount);
        }

        if (!enabled) {
            logger.info("Redis accounting publishing disabled (accounting.redis.enabled=false)");
            return;
        }

        String host = env.getRequiredProperty("accounting.redis.host", String.class);
        int port = env.getRequiredProperty("accounting.redis.port", Integer.class);
        client = RedisClient.create(RedisURI.create(host, port));
        connection = client.connect();
        commands = connection.sync();
        scriptSha = commands.scriptLoad(RELEASE_LUA);
        logger.info("Redis accounting publishing enabled, connected to {}:{} (script SHA {})", host,
                port, scriptSha);
    }

    @PreDestroy
    public void shutdown() {
        if (connection != null) {
            connection.close();
        }
        if (client != null) {
            client.shutdown();
        }
    }

    @Override
    public void publishRelease(VirtualProc proc) {
        if (!enabled) {
            return;
        }
        try {
            evalRelease(proc);
        } catch (RedisNoScriptException ns) {
            // Lua script flushed (e.g., Redis restart with SCRIPT FLUSH). Reload and retry once.
            try {
                scriptSha = commands.scriptLoad(RELEASE_LUA);
                evalRelease(proc);
            } catch (Exception retry) {
                logger.warn(
                        "Redis publish retry failed for proc {} (show {}): {}; recompute "
                                + "will heal",
                        proc.getProcId(), proc.getShowId(), retry.getMessage());
            }
        } catch (Exception e) {
            // §4.3 row 1: publish failure -> Redis missing a decrement -> next recompute
            // (≤2 min) heals from SUM(proc). Log + swallow.
            logger.warn("Redis publish failed for proc {} (show {}): {}; recompute will heal",
                    proc.getProcId(), proc.getShowId(), e.getMessage());
        }
    }

    /**
     * Cuebot stores cores as centicores (cores × 100; see VirtualProc.java:143). Redis stores cores
     * (design §0 unit invariant), so we divide on the way out. The divide is exact: VirtualProc
     * forces coresReserved to a multiple of 100 at booking time.
     */
    static final int CENTICORES_PER_CORE = 100;

    private void evalRelease(VirtualProc proc) {
        String[] keys = new String[] {"acct:sub:" + proc.getShowId() + ":" + proc.getAllocationId(),
                "acct:folder:" + proc.folderId, "acct:job:" + proc.getJobId(),
                "acct:layer:" + proc.getLayerId(),
                "acct:point:" + proc.deptId + ":" + proc.getShowId(), "acct:seq"};
        String negCores = String.valueOf(-proc.coresReserved / CENTICORES_PER_CORE);
        String negGpus = String.valueOf(-proc.gpusReserved);
        String[] argv = new String[] {negCores, negGpus, negCores, negGpus, negCores, negGpus,
                negCores, negGpus, negCores, negGpus};
        commands.evalsha(scriptSha, ScriptOutputType.INTEGER, keys, argv);
    }

    @Override
    public boolean isEnabled() {
        return enabled;
    }
}
