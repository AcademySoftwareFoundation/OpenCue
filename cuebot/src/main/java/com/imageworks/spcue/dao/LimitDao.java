
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

package com.imageworks.spcue.dao;

import java.sql.Timestamp;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;

import com.imageworks.spcue.LimitEntity;
import com.imageworks.spcue.LimitInterface;
import com.imageworks.spcue.LimitRule;
import com.imageworks.spcue.grpc.limit.LimitBindSource;
import com.imageworks.spcue.grpc.limit.LimitBinding;
import com.imageworks.spcue.grpc.limit.LimitEnforcement;
import com.imageworks.spcue.grpc.limit.LimitHold;
import com.imageworks.spcue.grpc.limit.LimitHostUsage;
import com.imageworks.spcue.grpc.limit.LimitType;

public interface LimitDao {

    /**
     * Insert and return the id of a new limit.
     *
     * @param name limit name, unique
     * @param maxValue maximum tokens; for a HOST limit, the maximum number of distinct machines the
     *        farm may spread across
     * @param type how the limit counts tokens
     * @param enforcement whether the limit gates booking or only informs it
     * @param softValue usage above which only already-holding hosts may book; -1 = same as max
     * @return the new limit's id
     */
    String createLimit(String name, int maxValue, LimitType type, LimitEnforcement enforcement,
            int softValue);

    /**
     * Insert and return the id of a new limit.
     *
     * @deprecated use the full overload. Creates an ENFORCED FRAME limit.
     */
    @Deprecated
    String createLimit(String name, int maxValue);

    /**
     * Deletes a limit record, if possible.
     *
     * @param limit
     */
    void deleteLimit(LimitInterface limit);

    /**
     * Find a limit by its name
     *
     * @param name
     * @return LimitEntity
     */
    LimitEntity findLimit(String name);

    /**
     * Returns the subset of the given names that have no matching limit record. Names are returned
     * in the order they were given, without duplicates.
     *
     * @param names
     * @return names that do not exist
     */
    public List<String> findMissingLimitNames(Collection<String> names);

    /**
     * Gets a limit by Id
     *
     * @param id
     * @return LimitEntity
     */
    LimitEntity getLimit(String id);

    /**
     * Gets every limit.
     */
    List<LimitEntity> getLimits();

    /**
     * Set the specified limit's name.
     *
     * @param limit
     * @param name
     */
    void setLimitName(LimitInterface limit, String name);

    /**
     * Set the specified limit's max value.
     *
     * @param limit
     * @param value
     */
    void setMaxValue(LimitInterface limit, int value);

    /**
     * Set the usage above which only hosts already holding a token may book. -1 means "same as max
     * value".
     */
    void setSoftValue(LimitInterface limit, int value);

    /**
     * Set how the limit counts tokens: per frame or per host.
     */
    void setLimitType(LimitInterface limit, LimitType type);

    /**
     * Set whether the limit gates booking, only informs it, or is ignored.
     */
    void setEnforcement(LimitInterface limit, LimitEnforcement enforcement);

    /**
     * Set the seconds after which an external report is stale. 0 disables staleness.
     */
    void setReportTtl(LimitInterface limit, int seconds);

    /**
     * Set the limit's failure rule: the frame exit status that means "this license was
     * unavailable", the layer backoff it triggers, and whether the failing layer is bound to the
     * limit. A null exitStatus clears the rule; existing AUTO bindings are left in place.
     */
    void setFailureRule(LimitInterface limit, Integer exitStatus, int delayMinutes,
            boolean autoTag);

    /**
     * All configured failure rules, keyed by exit status. Feeds the rule cache.
     */
    Map<Integer, LimitRule> getFailureRules();

    /**
     * Layers bound to a limit, optionally filtered by how they were bound and by layer. An empty
     * source set means all origins; an empty layer id collection means all layers.
     */
    List<LimitBinding> getBindings(LimitInterface limit, Set<LimitBindSource> sources,
            Collection<String> layerIds);

    /**
     * Remove bindings from a limit, scoped by origin. SPEC bindings are never removed here.
     *
     * @return rows removed
     */
    int clearBindings(LimitInterface limit, Set<LimitBindSource> sources);

    /**
     * Atomically claim the report watermark for one limit: advances ts_reported to captureTime only
     * when the stored watermark is absent, not newer than captureTime, and at least minIntervalMs
     * old. This conditional update is the authoritative admission for a report; unlocked
     * read-then-check admission would let two concurrent reporters both pass and an older snapshot
     * overwrite a newer one.
     *
     * @return true when the watermark was claimed and the caller may replace the holds
     */
    boolean claimReportWatermark(LimitInterface limit, Timestamp captureTime, String source,
            long minIntervalMs);

    /**
     * Apply a report as a delta against the current hold set and advance the limit's settlement
     * watermark. Runs in the caller's transaction. Written as an upsert-and-sweep rather than a
     * delete-and-insert so an unchanged holder produces no new row version and the table never
     * bloats.
     */
    void replaceExternalHolds(LimitInterface limit, List<LimitHostUsage> holds, String source,
            Timestamp captureTime);

    /**
     * Recompute one limit_usage row. Called by the report path so a fresh report takes effect on
     * the next dispatch rather than on the next timer tick.
     */
    void refreshUsage(LimitInterface limit);

    /**
     * Recompute every limit_usage row. Called by the maintenance task.
     */
    void refreshAllUsage();

    /**
     * Current token holders for one limit: external holds merged with hosts running frames of bound
     * layers.
     */
    List<LimitHold> getHolds(LimitInterface limit, String hostName);

    /**
     * Current token holders across every limit, optionally narrowed to one host.
     *
     * @param hostName short name or FQDN; null or empty returns every host
     */
    List<LimitHold> getHolds(String hostName);
}
