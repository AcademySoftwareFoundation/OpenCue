
/*
 * Copyright (c) 2018 Sony Pictures Imageworks Inc.
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



package com.imageworks.spcue.service;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

import org.apache.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.ActionEntity;
import com.imageworks.spcue.ActionInterface;
import com.imageworks.spcue.FilterEntity;
import com.imageworks.spcue.FilterInterface;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.Inherit;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.MatcherEntity;
import com.imageworks.spcue.MatcherInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.dao.ActionDao;
import com.imageworks.spcue.dao.FilterDao;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.MatcherDao;
import com.imageworks.spcue.grpc.filter.ActionType;
import com.imageworks.spcue.grpc.filter.FilterType;
import com.imageworks.spcue.grpc.job.LayerType;
import com.imageworks.spcue.util.Convert;

// TODO: add filter caching

/**
 * The filter manager handles all spank filtering and manipulation
 * of filters, actions, and matchers.
 *
 * @category Service
 */
@Service
@Transactional
public class FilterManagerService implements FilterManager {

    private static final Logger logger = Logger.getLogger(FilterManagerService.class);

    @Autowired
    private ActionDao actionDao;

    @Autowired
    private MatcherDao matcherDao;

    @Autowired
    private FilterDao filterDao;

    @Autowired
    private GroupDao groupDao;

    @Autowired
    private JobDao jobDao;

    @Autowired
    private LayerDao layerDao;

    @Transactional(propagation = Propagation.SUPPORTS)
    public void runFilter(FilterEntity filter) {
        List<JobDetail> jobs = jobDao.findJobs(filter);
        for (JobDetail job: jobs) {
            if(!match(filter, job)) {
                continue;
            }
            applyActions(filter,job);
        }
    }

    @Transactional(propagation = Propagation.SUPPORTS)
    public void runFilterOnJob(FilterEntity filter, JobDetail job) {
        if (match(filter,job)) {
            applyActions(filter,job);
        }
    }

    @Transactional(propagation = Propagation.SUPPORTS)
    public void runFilterOnJob(FilterEntity filter, String id) {
        JobDetail j = jobDao.getJobDetail(id);
        if (match(filter, j)) {
            applyActions(filter,j);
        }
    }

    @Transactional(propagation = Propagation.SUPPORTS)
    public void runFilterOnGroup(FilterEntity filter, GroupInterface group) {
        for (JobDetail job: jobDao.findJobs(group)) {
            if (match(filter,job)) {
                applyActions(filter,job);
            }
        }
    }

    @Transactional(propagation = Propagation.SUPPORTS)
    public void filterShow(ShowInterface show) {

        List<FilterEntity> filters = filterDao.getActiveFilters(show);
        List<JobDetail> jobs = jobDao.findJobs(show);

        for (JobDetail job: jobs) {
            for (FilterEntity filter: filters) {
                if (!match(filter,job)) {
                    continue;
                }
                boolean stopProcessing = applyActions(filter,job);
                if (stopProcessing) {
                    break;
                }
            }
        }
    }
    public void deleteFilter(FilterInterface f) {
        filterDao.deleteFilter(f);
    }

    public void lowerFilterOrder(FilterInterface f) {
        filterDao.lowerFilterOrder(f, 1);
    }

    public void raiseFilterOrder(FilterInterface f) {
        filterDao.raiseFilterOrder(f, 1);
    }

    public void setFilterOrder(FilterInterface f, double order) {
        filterDao.updateSetFilterOrder(f, order);
    }

    public void createAction(ActionEntity action) {
        actionDao.createAction(action);
    }

    public void createMatcher(MatcherEntity matcher) {
        matcherDao.insertMatcher(matcher);
    }

    /**
     * Stores what options have already been set by other
     * filers.  Will need to extend this later to handle
     * jobs running through different filers.
     */
    public class Context {

        public static final int SET_MIN_CORES = 1;
        public static final int SET_MAX_CORES = 2;
        public static final int SET_PRIORITY  = 4;

        int props = 0;

        public void setProperty(int value) {
            if ((props & value) != value) {
                props = props + value;
            }
        }

        public boolean isSet(int value) {
            return (props & value) == value;
        }
    }

    /**
     * Take a new job detail and run it though the
     * show's filters, setting the groupId property.

     * @param job
     */
    @Transactional(propagation = Propagation.SUPPORTS)
    public void runFiltersOnJob(JobDetail job) {
        Context context = new Context();
        List<FilterEntity> filters = filterDao.getActiveFilters(job);
        for (FilterEntity filter : filters) {
            if(match(filter, job)) {
                boolean stop_filters = applyActions(filter, job, context);
                if (stop_filters) { break; }
            }
        }
    }

    public boolean applyActions(List<ActionEntity> actions, JobDetail job, Context context) {
        for (ActionEntity action: actions) {
            applyAction(action, job, context);
            if (action.type.equals(ActionType.STOP_PROCESSING)) {
                return true;
            }
        }
        return false;
    }

    public boolean applyActions(List<ActionEntity> actions, JobDetail job) {
        return applyActions(actions, job, new Context());
    }

    public boolean applyActions(FilterEntity filter, JobDetail job) {
        return applyActions(filter, job, new Context());
    }

    public boolean applyActions(FilterEntity filter, JobDetail job, Context context) {
       return applyActions(actionDao.getActions(filter), job, context);
    }

    private boolean isMatch(final MatcherEntity matcher, final String ... inputs) {
        boolean isMatch = false;

        switch (matcher.type) {
            case CONTAINS:
                for (String s : inputs) {
                    isMatch = s.contains(matcher.value);
                    if (isMatch) break;
                }
                break;
            case DOES_NOT_CONTAIN:
                for (String s : inputs) {
                    isMatch = s.contains(matcher.value);
                    if (isMatch) return false;
                }
                isMatch = true;
                break;
            case IS:
                for (String s : inputs) {
                    isMatch = s.equals(matcher.value);
                    if (isMatch) break;
                }
                break;
            case IS_NOT:
                for (String s : inputs) {
                    isMatch = s.equals(matcher.value);
                    if (isMatch) return false;
                }
                isMatch = true;
                break;
            case BEGINS_WITH:
                for (String s : inputs) {
                    isMatch = s.startsWith(matcher.value);
                    if (isMatch) break;
                }
                break;
            case ENDS_WITH:
                for (String s : inputs) {
                    isMatch = s.endsWith(matcher.value);
                    if (isMatch) break;
                }
                break;
            case REGEX:
                Pattern pattern = null;
                try {
                    pattern = Pattern.compile(matcher.value);
                } catch (Exception e) {
                    return false;
                }

                for (String s : inputs) {
                    isMatch = pattern.matcher(s).find();
                    if (isMatch) break;
                }
                break;
        }
        return isMatch;
    }

    public boolean isMatch(MatcherEntity matcher, JobDetail job) {

        String input = null;

        switch (matcher.subject) {
            case SERVICE_NAME: {
                List<LayerDetail> layers = layerDao.getLayerDetails(job);
                List<String> serviceNames = new ArrayList<String>(layers.size());
                for (LayerDetail layer : layers) {
                    for (String service : layer.services) {
                        serviceNames.add(service);
                    }
                }

                return isMatch(matcher, serviceNames.toArray(new String[0]));
            }
            case LAYER_NAME: {
                List<LayerDetail> layers = layerDao.getLayerDetails(job);
                List<String> layerNames = new ArrayList<String>(layers.size());
                for (LayerDetail layer : layers) {
                    layerNames.add(layer.name);
                }

                return isMatch(matcher, layerNames.toArray(new String[0]));
            }
            default: {
                switch (matcher.subject) {
                    case JOB_NAME:
                        input = job.getName().toLowerCase();
                        break;
                    case SHOW:
                        input = job.showName.toLowerCase();
                        break;
                    case SHOT:
                        input = job.shot.toLowerCase();
                        break;
                    case USER:
                        input = job.user.toLowerCase();
                        break;
                    case PRIORITY:
                        input = Integer.toString(job.priority);
                        break;
                    case FACILITY:
                        if (job.facilityName == null) {
                            return false;
                        }
                        input = job.facilityName.toLowerCase();
                        break;
                    default:
                        input = "";
                }

                return isMatch(matcher, input);
            }
        }
    }

    public boolean applyAction(ActionEntity action, JobDetail job) {
        return applyAction(action, job, new Context());
    }

    public boolean applyAction(ActionEntity action, JobDetail job, Context context) {

        boolean stopProcessing = false;
        /**
         * All of these actions can be handled by the call
         * to updateJob which happens later on.  All other
         * actions are handlded in applyAction
         */
        switch(action.type) {
            case PAUSE_JOB:
                jobDao.updatePaused(job, action.booleanValue);
                break;

            case SET_JOB_MIN_CORES:
                context.setProperty(Context.SET_MIN_CORES);
                jobDao.updateMinCores(job, Convert.coresToCoreUnits(action.floatValue));
                break;

            case SET_JOB_MAX_CORES:
                context.setProperty(Context.SET_MAX_CORES);
                jobDao.updateMaxCores(job, Convert.coresToCoreUnits(action.floatValue));
                break;

            case SET_JOB_PRIORITY:
                context.setProperty(Context.SET_PRIORITY);
                int priority = (int) action.intValue;
                jobDao.updatePriority(job, priority);
                job.priority = priority;
                break;

            case MOVE_JOB_TO_GROUP:
                // Just ignore this if the groupValue is null.  The job will launch
                // and it can be moved to the right group manually.
                if (action.groupValue == null) {
                    logger.error("Did not move job to group, the group value was not valid.");
                    break;
                }

                GroupDetail g = groupDao.getGroupDetail(action.groupValue);
                List<Inherit> inherits = new ArrayList<Inherit>(3);

                // Do not set these values from the group if they were set by another filter.
                if (!context.isSet(Context.SET_PRIORITY) && g.jobPriority != -1) {
                    inherits.add(Inherit.Priority);
                }
                if (!context.isSet(Context.SET_MAX_CORES)  && g.jobMaxCores != -1) {
                    inherits.add(Inherit.MaxCores);
                }
                if (!context.isSet(Context.SET_MIN_CORES) && g.jobMinCores != -1) {
                    inherits.add(Inherit.MinCores);
                }

                logger.info("moving job into group: " + g.name);
                jobDao.updateParent(job, g, inherits.toArray(new Inherit[0]));
                break;

            case SET_ALL_RENDER_LAYER_TAGS:
                layerDao.updateTags(job, action.stringValue, LayerType.RENDER);
                break;

            case SET_ALL_RENDER_LAYER_MEMORY:
                layerDao.updateMinMemory(job, (int) action.intValue, LayerType.RENDER);
                break;

            case SET_ALL_RENDER_LAYER_CORES:
                layerDao.updateMinCores(job, Convert.coresToCoreUnits(action.floatValue), LayerType.RENDER);
                break;

            case SET_MEMORY_OPTIMIZER:
                List<LayerInterface> layers =  layerDao.getLayers(job);
                for (LayerInterface layer : layers) {
                    layerDao.enableMemoryOptimizer(layer, action.booleanValue);
                }
                break;

            default:
                stopProcessing = true;
                break;
        }

        return stopProcessing;
    }

    private boolean match(FilterEntity filter, JobDetail job) {

        int numMatched = 0;
        int numMatchesRequired = 1;

        List<MatcherEntity> matchers = matcherDao.getMatchers(filter);
        if (matchers.size() == 0) { return false; }

        if (filter.type.equals(FilterType.MATCH_ALL)) {
            numMatchesRequired = matchers.size();
        }

        for (MatcherEntity matcher: matchers) {
            boolean itMatches = isMatch(matcher,job);

            if (!itMatches) {
                if (filter.type.equals(FilterType.MATCH_ALL)) {
                    break;
                }
            }
            else {
                numMatched++;
                if (filter.type.equals(FilterType.MATCH_ANY)) {
                    break;
                }
            }
        }

        if (numMatched == numMatchesRequired) {
            return true;
        }

        return false;
    }

    public FilterDao getFilterDao() {
        return filterDao;
    }

    public void setFilterDao(FilterDao filterDao) {
        this.filterDao = filterDao;
    }

    public GroupDao getGroupDao() {
        return groupDao;
    }

    public void setGroupDao(GroupDao groupDao) {
        this.groupDao = groupDao;
    }

    public void deleteAction(ActionInterface action) {
        actionDao.deleteAction(action);
    }

    public void deleteMatcher(MatcherInterface matcher) {
        matcherDao.deleteMatcher(matcher);
    }

    public ActionEntity getAction(String id) {
        return actionDao.getAction(id);
    }

    public ActionEntity getAction(ActionInterface action) {
        return actionDao.getAction(action);
    }

    public FilterEntity getFilter(String id) {
        return filterDao.getFilter(id);
    }

    public FilterEntity getFilter(FilterInterface filter) {
        return filterDao.getFilter(filter);
    }

    public MatcherEntity getMatcher(String id) {
        return matcherDao.getMatcher(id);
    }

    public MatcherEntity getMatcher(MatcherInterface matcher) {
        return matcherDao.getMatcher(matcher);
    }

    public void updateAction(ActionEntity action) {
        actionDao.updateAction(action);
    }

    public void updateMatcher(MatcherEntity matcher) {
        matcherDao.updateMatcher(matcher);
    }

    public void createFilter(FilterEntity filter) {
        filterDao.insertFilter(filter);
    }

    public ActionDao getActionDao() {
        return actionDao;
    }

    public void setActionDao(ActionDao actionDao) {
        this.actionDao = actionDao;
    }

    public JobDao getJobDao() {
        return jobDao;
    }

    public void setJobDao(JobDao jobDao) {
        this.jobDao = jobDao;
    }

    public MatcherDao getMatcherDao() {
        return matcherDao;
    }

    public void setMatcherDao(MatcherDao matcherDao) {
        this.matcherDao = matcherDao;
    }

    public LayerDao getLayerDao() {
        return layerDao;
    }

    public void setLayerDao(LayerDao layerDao) {
        this.layerDao = layerDao;
    }
}

