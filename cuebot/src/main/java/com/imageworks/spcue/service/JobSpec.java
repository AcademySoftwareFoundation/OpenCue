
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



package com.imageworks.spcue.service;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.StringReader;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.log4j.Logger;
import org.jdom.Document;
import org.jdom.Element;
import org.jdom.input.SAXBuilder;
import org.springframework.dao.EmptyResultDataAccessException;
import org.xml.sax.EntityResolver;
import org.xml.sax.InputSource;
import org.xml.sax.SAXException;

import com.imageworks.spcue.BuildableDependency;
import com.imageworks.spcue.BuildableJob;
import com.imageworks.spcue.BuildableLayer;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.ServiceEntity;
import com.imageworks.spcue.SpecBuilderException;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.depend.DependType;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.job.LayerType;
import com.imageworks.spcue.util.Convert;
import com.imageworks.spcue.util.CueUtil;

public class JobSpec {
    private static final Logger logger = Logger.getLogger(JobSpec.class);

    private String facility;

    private String show;

    private String shot;

    private String user;

    private String email;

    private Optional<Integer> uid;

    private int totalFrames = 0;

    private Document doc;

    private ServiceManager serviceManager;

    /**
     * Maximum number of cores a layer can get per frame.
     */
    public static final int MAX_CORES = 800;

    /**
     * The maximum number of layers a job can have. Increases this with care,
     * its usually not worth it. The more layers you have the longer a job takes
     * to dispatch which could lead to dispatches being dropped.
     */
    public static final int MAX_LAYERS = 1000;

    /**
     * The maximum number of frames a job can have. Increase this with care. The
     * more frames a job has, the longer it takes to dispatch, which could lead
     * to dispatches being dropped.
     */
    public static final int MAX_FRAMES = 100000;

    // The default number of retries per frame
    public static final int FRAME_RETRIES_DEFAULT = 1;

    // The default maximum number of retries per frame.
    public static final int FRAME_RETRIES_MAX = 1;

    // The default minimum number of retries per frame.
    public static final int FRAME_RETRIES_MIN = 0;

    public static final String DEFAULT_SERVICE = "default";

    public static final String SPCUE_DTD_URL = "http://localhost:8080/spcue/dtd/";

    private List<BuildableJob> jobs = new ArrayList<BuildableJob>();

    private List<BuildableDependency> depends = new ArrayList<BuildableDependency>();

    public JobSpec() {
    }

    public static final String NAME_REGEX = "^([\\w\\.]{3,})$";

    public static final Pattern NAME_PATTERN = Pattern.compile(NAME_REGEX);

    public String conformJobName(String name) {

        if (name == null) {
            throw new SpecBuilderException("Job names cannot be null");
        }

        String prefix = String.format("%s-%s-%s_", show, shot, user);
        String suffix = name;

        /*
         * Find the job's suffix
         */
        if (suffix.startsWith(prefix)) {
            int index = prefix.length() - 1;
            suffix = suffix.substring(index);
        }

        suffix = suffix.toLowerCase();
        suffix = suffix.replaceAll("[_]{2,}", "_");

        suffix = suffix.replace("-", "_");

        Matcher matcher = NAME_PATTERN.matcher(suffix);
        if (!matcher.matches()) {
            throw new SpecBuilderException(
                    "The job name suffix: "
                            + suffix
                            + " must be composed of alpha numeric characters, periods, "
                            + "and underscores and be at least 3 characters long");
        }

        suffix = suffix.replaceAll("^[_]{1,}", "");
        prefix = prefix.replaceAll("[_]{1,}$", "");

        return String.format("%s_%s", prefix, suffix).toLowerCase();
    }

    public static String conformName(String type, String name) {

         String lowerType = type.toLowerCase();

        if (name.length() < 3) {
            throw new SpecBuilderException(
                    "The " + lowerType + " name must be at least 3 characters.");
        }

        String newName = name;
        newName = newName.replace("-", "_");
        newName = newName.toLowerCase();

        Matcher matcher = NAME_PATTERN.matcher(newName);
        if (!matcher.matches()) {
            throw new SpecBuilderException("The " + lowerType + " name: " + newName
                    + " is not in the proper format.  " + type + " names must be "
                    + "alpha numeric, no dashes or punctuation.");
        }

        return newName;
    }

    public static String conformShowName(String name) {
        return conformName("Show", name);
    }

    public static String conformShotName(String name) {
        return conformName("Shot", name);
    }

    public static String conformLayerName(String name) {
        return conformName("Layer", name);
    }

    public static final String FRAME_NAME_REGEX = "^([\\d]{4,6})-([\\w]+)$";

    public static final Pattern FRAME_NAME_PATTERN = Pattern
            .compile(FRAME_NAME_REGEX);

    public String conformFrameName(String name) {
        Matcher m = FRAME_NAME_PATTERN.matcher(name);
        if (!m.matches()) {
            throw new SpecBuilderException("The frame name: " + name
                    + " is not in the proper format.");
        }
        return String.format("%04d-%s", Integer.valueOf(m.group(1)),
                conformLayerName(m.group(2)));
    }

    /**
     * Grabs the show/shot/user/uid for this spec.
     */
    private void handleSpecTag() {
        Element rootElement = doc.getRootElement();
        facility = rootElement.getChildTextTrim("facility");
        if (facility != null) {
            facility = facility.toLowerCase();
        }

        show = rootElement.getChildTextTrim("show");
        shot = conformShotName(rootElement.getChildTextTrim("shot"));
        user = rootElement.getChildTextTrim("user");
        uid = Optional.ofNullable(rootElement.getChildTextTrim("uid")).map(Integer::parseInt);
        email = rootElement.getChildTextTrim("email");

        if (user.equals("root") || uid.equals(Optional.of(0))) {
            throw new SpecBuilderException("Cannot launch jobs as root.");
        }
    }

    /**
     * Loop over all <job> tags
     *
     */
    private void handleJobsTag() {
        List<?> elements = doc.getRootElement().getChildren("job");
        if (elements == null) {
            return;
        }

        for (Object tmpElement : elements) {
            Element jobElement = (Element) tmpElement;
            jobs.add(handleJobTag(jobElement));
        }
    }

    /**
     * Loop over all <depend> tags
     *
     */
    private void handleDependsTags() {
        Element delements = doc.getRootElement().getChild("depends");
        if (delements == null) {
            return;
        }
        List<?> elements = delements.getChildren("depend");
        if (elements == null) {
            return;
        }
        for (Object tmpElement : elements) {
            Element dependElement = (Element) tmpElement;
            depends.add(handleDependTag(dependElement));
        }
    }

    /**
     *
     * @param jobTag
     * @return
     */
    private BuildableJob handleJobTag(Element jobTag) {

        /*
         * Read in the job tag
         */
        JobDetail job = new JobDetail();
        job.name = conformJobName(jobTag.getAttributeValue("name"));
        job.state = JobState.STARTUP;
        job.isPaused = Convert.stringToBool(jobTag.getChildTextTrim("paused"));
        job.isAutoEat = Convert.stringToBool(jobTag.getChildTextTrim("autoeat"));
        job.isLocal = false;
        Element local = jobTag.getChild("localbook");
        if (local != null) {
            job.isLocal = true;
            job.localHostName = local.getAttributeValue("host");
            if (local.getAttributeValue("cores") != null)
                job.localMaxCores = Integer.parseInt(local.getAttributeValue("cores"));
            if (local.getAttributeValue("memory") != null)
                job.localMaxMemory = Long.parseLong(local.getAttributeValue("memory"));
            if (local.getAttributeValue("threads") != null)
                job.localThreadNumber = Integer.parseInt(local.getAttributeValue("threads"));
            if (local.getAttributeValue("gpus") != null)
                job.localMaxGpus = Integer.parseInt(local.getAttributeValue("gpus"));
            if (local.getAttributeValue("gpu") != null) {
                logger.warn(job.name + " localbook has the deprecated gpu. Use gpu_memory.");
                job.localMaxGpuMemory = Long.parseLong(local.getAttributeValue("gpu"));
            }
            if (local.getAttributeValue("gpu_memory") != null)
                job.localMaxGpuMemory = Long.parseLong(local.getAttributeValue("gpu_memory"));
        }

        job.maxCoreUnits = 20000;
        job.minCoreUnits = 100;
        job.startTime = CueUtil.getTime();
        job.maxRetries = FRAME_RETRIES_DEFAULT;
        job.shot = shot;
        job.user = user;
        job.uid = uid;
        job.email = email;
        job.os = null; // default to no OS specified
        job.showName = show;
        job.facilityName = facility;
        job.deptName = jobTag.getChildTextTrim("dept");

        BuildableJob buildableJob = new BuildableJob(job);

        if (jobTag.getChildTextTrim("os") != null) {
            job.os = jobTag.getChildTextTrim("os");
        }

        if (jobTag.getChildTextTrim("maxretries") != null) {
            job.maxRetries = Integer.valueOf(jobTag
                    .getChildTextTrim("maxretries"));
            if (job.maxRetries > FRAME_RETRIES_MAX) {
                job.maxRetries = FRAME_RETRIES_MAX;
            } else if (job.maxRetries < FRAME_RETRIES_MIN) {
                job.maxRetries = FRAME_RETRIES_MIN;
            }
        }

        if (jobTag.getChildTextTrim("priority") != null) {
            job.priority = Integer.valueOf(jobTag.getChildTextTrim("priority"));
        }

        handleLayerTags(buildableJob, jobTag);

        if (buildableJob.getBuildableLayers().size() > MAX_LAYERS) {
            throw new SpecBuilderException("The job " + job.name + " has over "
                    + MAX_LAYERS + " layers");
        }

        if (buildableJob.getBuildableLayers().size() < 1) {
            throw new SpecBuilderException("The job " + job.name
                    + " has no layers");
        }

        Element envTag = jobTag.getChild("env");
        if (envTag != null) {
            handleEnvironmentTag(envTag, buildableJob.env);
        }

        return buildableJob;
    }

    /**
     *
     * @param buildableJob
     * @param jobTag
     */
    private void handleLayerTags(BuildableJob buildableJob, Element jobTag) {

        Set<String> layerNames = new HashSet<String>();
        int dispatchOrder = 0;

        for (Object layerTmp : jobTag.getChild("layers").getChildren("layer")) {

            Element layerTag = (Element) layerTmp;

            /*
             * Setup a LayerDetail and Buildable layer, add layer to job
             */
            LayerDetail layer = new LayerDetail();
            BuildableLayer buildableLayer = new BuildableLayer(layer);

            /*
             * Setup the layer type
             */
            String layerType = layerTag.getAttributeValue("type");
            /*
             * The Enum is capitalized so make sure that we capitalize the
             * string we received from the user.
             */
            layer.type = LayerType.valueOf(layerType.toUpperCase());
            if (layer.type == null) {
                throw new SpecBuilderException("error, the layer " + layer.name
                        + " was defined with an invalid type: "
                        + layerTag.getAttributeValue("type"));
            }

            /*
             * If the layer is a post layer, we add it to the post job.
             */
            if (layer.type.equals(LayerType.POST)) {
                if (buildableJob.getPostJob() == null) {
                    buildableJob.setPostJob(initPostJob(buildableJob));
                }
                buildableJob.getPostJob().addBuildableLayer(buildableLayer);
            } else {
                buildableJob.addBuildableLayer(buildableLayer);
            }

            /*
             * Check to make sure the name is unique for this job.
             */
            if (layerTag.getAttributeValue("name") == null) {
                throw new SpecBuilderException(
                        "error, the layer name cannot be null");
            }

            layer.name = conformLayerName(layerTag.getAttributeValue("name"));

            if (layerNames.contains(layer.name)) {
                throw new SpecBuilderException("error, the layer " + layer.name
                        + " was already defined in job "
                        + buildableJob.detail.name);
            }
            layerNames.add(layer.name);

            /*
             * Setup the simple layer properties.
             */
            layer.command = layerTag.getChildTextTrim("cmd");
            layer.range = layerTag.getChildTextTrim("range");
            layer.dispatchOrder = ++dispatchOrder;

            /*
             * Determine some of the more complex attributes.
             */
            determineResourceDefaults(layerTag, buildableJob, layer);
            determineChunkSize(layerTag, layer);
            determineMinimumCores(layerTag, layer);
            determineMinimumGpus(layerTag, layer);
            determineThreadable(layerTag, layer);
            determineTags(buildableJob, layer, layerTag);
            determineMinimumMemory(buildableJob, layerTag, layer,
                    buildableLayer);
            determineMinimumGpuMemory(buildableJob, layerTag, layer);

            // set a timeout value on the layer
            if (layerTag.getChildTextTrim("timeout") != null) {
                layer.timeout = Integer.parseInt(layerTag.getChildTextTrim("timeout"));
            }

            if (layerTag.getChildTextTrim("timeout_llu") != null) {
                layer.timeout_llu = Integer.parseInt(layerTag.getChildTextTrim("timeout_llu"));
            }

            /*
             * Handle the layer environment
             */
            Element envTag = layerTag.getChild("env");
            if (envTag != null) {
                handleEnvironmentTag(envTag, buildableLayer.env);
            }

            totalFrames = totalFrames
                    + getFrameRangeSize(layer.range, layer.chunkSize);

            if (buildableJob.getBuildableLayers().size() > MAX_LAYERS) {
                throw new SpecBuilderException("error, your job has "
                        + buildableJob.getBuildableLayers().size()
                        + " layers, "
                        + " the maximum number of allowed layers is "
                        + MAX_LAYERS);
            }

            if (totalFrames > MAX_FRAMES) {
                throw new SpecBuilderException("error, your job has "
                        + totalFrames
                        + " frames, the maximum number of allowed "
                        + "frames is " + MAX_FRAMES);
            }
        }
    }

    /**
     * Convert string given for memory, with m for megabytes or g for gigabytes
     * to kilobytes.
     *
     * @param input
     */
    private long convertMemoryInput(String input) {
        if (input.contains("m")) {
            double megs = Double.valueOf(input.substring(0, input.lastIndexOf("m")));
            return (long) (megs * 1024);
        } else if (input.contains("g")) {
            return Long.valueOf(input.substring(0, input.lastIndexOf("g"))) * CueUtil.GB;
        } else {
            return Long.valueOf(input) * CueUtil.GB;
        }
    }

    private void determineMinimumMemory(BuildableJob buildableJob,
            Element layerTag, LayerDetail layer, BuildableLayer buildableLayer) {

        if (layerTag.getChildTextTrim("memory") == null) {
            return;
        }

        long minMemory;
        String memory = layerTag.getChildTextTrim("memory").toLowerCase();

        try {
            minMemory = convertMemoryInput(memory);

            // Some quick sanity checks to make sure memory hasn't gone
            // over or under reasonable defaults.
            if (minMemory> Dispatcher.MEM_RESERVED_MAX) {
                throw new SpecBuilderException("Memory requirements exceed " +
                        "maximum. Are you specifying the correct units?");
            }
            else if (minMemory < Dispatcher.MEM_RESERVED_MIN) {
                logger.warn(buildableJob.detail.name + "/" + layer.name +
                        "Specified too little memory, defaulting to: " +
                        Dispatcher.MEM_RESERVED_MIN);
                minMemory = Dispatcher.MEM_RESERVED_MIN;
            }

            buildableLayer.isMemoryOverride = true;
            layer.minimumMemory = minMemory;

        } catch (Exception e) {
            logger.info("Setting setting memory for " +
                    buildableJob.detail.name + "/" + layer.name +
                    " failed, reason: " + e + ". Using default.");
            layer.minimumMemory = Dispatcher.MEM_RESERVED_DEFAULT;
        }
    }

    /**
     * If the gpu_memory option is set, set minimumGpuMemory to that supplied value
     *
     * @param layerTag
     * @param layer
     */
    private void determineMinimumGpuMemory(BuildableJob buildableJob, Element layerTag,
    		LayerDetail layer) {

        String gpu = layerTag.getChildTextTrim("gpu");
        String gpuMemory = layerTag.getChildTextTrim("gpu_memory");
        if (gpu == null && gpuMemory == null) {
            return;
        }

        String memory = null;
        if (gpu != null) {
            logger.warn(buildableJob.detail.name + "/" + layer.name +
                    " has the deprecated gpu. Use gpu_memory.");
            memory = gpu.toLowerCase();
        }
        if (gpuMemory != null)
            memory = gpuMemory.toLowerCase();

        long minGpuMemory;
        try {
            minGpuMemory = convertMemoryInput(memory);

            // Some quick sanity checks to make sure gpu memory hasn't gone
            // over or under reasonable defaults.
            if (minGpuMemory > Dispatcher.MEM_GPU_RESERVED_MAX) {
                throw new SpecBuilderException("Gpu memory requirements exceed " +
                        "maximum. Are you specifying the correct units?");
            }
            else if (minGpuMemory < Dispatcher.MEM_GPU_RESERVED_MIN) {
                logger.warn(buildableJob.detail.name + "/" + layer.name +
                        "Specified too little gpu memory, defaulting to: " +
                        Dispatcher.MEM_GPU_RESERVED_MIN);
                minGpuMemory = Dispatcher.MEM_GPU_RESERVED_MIN;
            }

            layer.minimumGpuMemory = minGpuMemory;

        } catch (Exception e) {
            logger.info("Error setting gpu memory for " +
                    buildableJob.detail.name + "/" + layer.name +
                    " failed, reason: " + e + ". Using default.");
            layer.minimumGpuMemory = Dispatcher.MEM_GPU_RESERVED_DEFAULT;
        }
    }

    /**
     * Cores may be specified as a decimal or core points.
     *
     * If no core value is specified, we default to the value of
     * Dispatcher.CORE_POINTS_RESERVED_DEFAULT
     *
     * If the value is specified but is less than the minimum allowed, then the
     * value is reset to the default.
     *
     * If the value is specified but is greater than the max allowed, then the
     * value is reset to the default.
     *
     */
    private void determineMinimumCores(Element layerTag, LayerDetail layer) {

        String cores = layerTag.getChildTextTrim("cores");
        if (cores == null) {
            return;
        }

        int corePoints = layer.minimumCores;

        if (cores.contains(".")) {
            corePoints = (int) (Double.valueOf(cores) * 100 + .5);
        } else {
            corePoints = Integer.valueOf(cores);
        }

        if (corePoints < Dispatcher.CORE_POINTS_RESERVED_MIN
                || corePoints > Dispatcher.CORE_POINTS_RESERVED_MAX) {
            corePoints = Dispatcher.CORE_POINTS_RESERVED_DEFAULT;
        }

        layer.minimumCores = corePoints;
    }

    /**
     * Gpu is a int.
     *
     * If no gpu value is specified, we default to the value of
     * Dispatcher.GPU_RESERVED_DEFAULT
     */
    private void determineMinimumGpus(Element layerTag, LayerDetail layer) {

        String gpus = layerTag.getChildTextTrim("gpus");
        if (gpus != null) {
            layer.minimumGpus = Integer.valueOf(gpus);
        }
    }

    private void determineChunkSize(Element layerTag, LayerDetail layer) {
        layer.chunkSize = Integer.parseInt(layerTag.getChildTextTrim("chunk"));
    }

    /**
     * Determine if the layer is threadable.  A manually set threadable
     * option in the job spec should override the service defaults.
     *
     * @param layerTag
     * @param layer
     */
    private void determineThreadable(Element layerTag, LayerDetail layer) {
        // Must have at least 1 core to thread.
        if (layer.minimumCores < 100) {
            layer.isThreadable = false;
        }
        else if (layerTag.getChildTextTrim("threadable") != null) {
            layer.isThreadable = Convert.stringToBool(
                    layerTag.getChildTextTrim("threadable"));
        }
    }

    private void determineResourceDefaults(Element layerTag,
            BuildableJob job, LayerDetail layer) {

        Element t_services = layerTag.getChild("services");
        List<String> services = new ArrayList<String>();

        /*
         * Build a list of services from the XML.  Filter
         * out duplicates and empty services.
         */
        if (t_services != null) {

            for (Object tmp : t_services.getChildren()) {
                Element t_service = (Element) tmp;
                String service_name = t_service.getTextTrim();

                if (service_name.length() == 0) {
                    continue;
                }

                if (services.contains(service_name)) {
                    continue;
                }
                services.add(service_name);
            }
        }

        /*
         * Start from the beginning and check each service.  The first
         * one that has a service record will be the one to use.
         */
        ServiceEntity primaryService = null;
        for (String service_name: services) {
            try {
                primaryService = serviceManager.getService(service_name,
                        job.detail.showName);
                // Once a service is found, break;
                break;
            } catch (EmptyResultDataAccessException e) {
                logger.warn("warning, service not found for layer " +
                        layer.getName() + " " + service_name);
            }
        }

        /*
         * If no primary service was found, use the default service.
         */
        if (primaryService == null) {
            primaryService = serviceManager.getService(DEFAULT_SERVICE);
            services.add(primaryService.name);
        }

        Element t_limits = layerTag.getChild("limits");
        List<String> limits = new ArrayList<String>();

        if (t_limits != null) {
            for (Object tmp : t_limits.getChildren()) {
                Element t_limit = (Element) tmp;
                String limitName = t_limit.getTextTrim();

                if (limitName.length() == 0) {
                    continue;
                }

                if (limits.contains(limitName)) {
                    continue;
                }
                limits.add(limitName);
            }
        }


        logger.info("primary service: " + primaryService.getName() + " " +
                layer.getName());

        /*
         *  Now apply the primaryService values to the layer.
         */
        layer.isThreadable = primaryService.threadable;
        layer.maximumCores = primaryService.maxCores;
        layer.minimumCores = primaryService.minCores;
        layer.minimumMemory = primaryService.minMemory;
        layer.maximumGpus = primaryService.maxGpus;
        layer.minimumGpus = primaryService.minGpus;
        layer.minimumGpuMemory = primaryService.minGpuMemory;
        layer.tags.addAll(primaryService.tags);
        layer.services.addAll(services);
        layer.limits.addAll(limits);
        layer.timeout = primaryService.timeout;
        layer.timeout_llu = primaryService.timeout_llu;
    }

    /**
     * Converts the job space tagging format into a set of strings. Also
     * verifies each tag.
     *
     * @param job
     * @param layer
     * @return
     */
    private void determineTags(BuildableJob job, LayerDetail layer,
            Element layerTag) {
        Set<String> newTags = new LinkedHashSet<String>();
        String tags = layerTag.getChildTextTrim("tags");

        if (tags == null) {
            return;
        }

        if (tags.length() == 0) {
            return;
        }

        String[] e = tags.replaceAll(" ", "").split("\\|");
        for (String s : e) {
            if (e.length == 0) {
                continue;
            }
            Matcher matcher = NAME_PATTERN.matcher(s);
            if (!matcher.matches()) {
                throw new SpecBuilderException("error, invalid tag " + s
                        + ", tags must be alpha numberic and at least "
                        + "3 characters in length.");
            }
            newTags.add(s);
        }

        if (newTags.size() > 0) {
            layer.tags = newTags;
        }
    }

    /**
     * Determine the frame range
     *
     * @param range
     * @param chunkSize
     * @return
     */
    public int getFrameRangeSize(String range, int chunkSize) {
        try {
            return CueUtil.normalizeFrameRange(range, chunkSize).size();
        } catch (Exception e) {
            throw new SpecBuilderException("error, the range " + range
                    + " is invalid");
        }
    }

    private BuildableDependency handleDependTag(Element tag) {

        BuildableDependency depend = new BuildableDependency();
        depend.type = DependType.valueOf(tag.getAttributeValue("type").toUpperCase());

        /*
         * If the depend type is layer on layer, allow dependAny to be set.
         * Depend any is not implemented for any other depend type.
         */
        if (depend.type.equals(DependType.LAYER_ON_LAYER)) {
            depend.anyFrame = Convert.stringToBool(tag
                    .getAttributeValue("anyframe"));
        }

        /*
         * Set job names
         */
        depend
                .setDependErJobName(conformJobName(tag
                        .getChildTextTrim("depjob")));
        depend
                .setDependOnJobName(conformJobName(tag
                        .getChildTextTrim("onjob")));

        /*
         * Set layer names
         */
        String depLayer = tag.getChildTextTrim("deplayer");
        String onLayer = tag.getChildTextTrim("onlayer");

        if (depLayer != null) {
            depend.setDependErLayerName(conformLayerName(depLayer));
        }
        if (onLayer != null) {
            depend.setDependOnLayerName(conformLayerName(onLayer));
        }

        /*
         * Set frame names
         */
        String depFrame = tag.getChildTextTrim("depframe");
        String onFrame = tag.getChildTextTrim("onframe");

        if (depFrame != null) {
            depFrame = conformFrameName(depFrame);
            depend.setDependErFrameName(depFrame);
        }
        if (onFrame != null) {
            onFrame = conformFrameName(onFrame);
            depend.setDependOnFrameName(onFrame);
        }

        // double check to make sure we don't have two of the same frame/
        if (onFrame != null && depFrame != null) {
            if (onFrame.equals(depFrame)) {
                throw new SpecBuilderException("The frame name: " + depFrame
                        + " cannot depend on itself.");
            }
        }

        return depend;
    }

    /**
     * Tags a env tag and populates the supplied map with key value pairs.
     *
     * @param tag
     * @param map
     */
    private void handleEnvironmentTag(Element tag, Map<String, String> map) {
        if (tag == null) {
            return;
        }
        for (Object tmp : tag.getChildren()) {
            Element envTag = (Element) tmp;
            String key = envTag.getAttributeValue("name");
            if (key == null) {
                continue;
            }
            map.put(key, envTag.getTextTrim());
        }
    }

    public void parse(File file) {
        try {
            doc = new SAXBuilder(true).build(file);

        } catch (Exception e) {
            throw new SpecBuilderException("Failed to parse job spec XML, " + e);
        }

        handleSpecTag();
        handleJobsTag();
        handleDependsTags();
    }

    private class DTDRedirector implements EntityResolver {
        public InputSource resolveEntity(String publicId,
                String systemId) throws SAXException, IOException {
            if (systemId.startsWith(SPCUE_DTD_URL)) {
                // Redirect to resource file.
                try {
                    String filename = systemId.substring(SPCUE_DTD_URL.length());
                    InputStream dtd = getClass().getResourceAsStream("/public/dtd/" + filename);
                    return new InputSource(dtd);
                } catch (Exception e) {
                    throw new SpecBuilderException("Failed to redirect DTD " + systemId + ", " + e);
                }
            } else {
                // Use default resolver.
                return null;
            }
        }
    }

    public void parse(String cjsl) {
        try {
            SAXBuilder builder = new SAXBuilder(true);
            builder.setEntityResolver(new DTDRedirector());
            doc = builder.build(new StringReader(cjsl));

        } catch (Exception e) {
            throw new SpecBuilderException("Failed to parse job spec XML, " + e);
        }

        handleSpecTag();
        handleJobsTag();
        handleDependsTags();
    }

    private BuildableJob initPostJob(BuildableJob parent) {

        JobDetail job = new JobDetail();
        job.name = parent.detail.name + "_post_job_"
                + System.currentTimeMillis();
        job.name = job.name.replace(user, "monitor");
        job.state = JobState.STARTUP;
        job.isPaused = false;
        job.maxCoreUnits = 500;
        job.startTime = CueUtil.getTime();
        job.maxRetries = 2;
        job.shot = shot;
        job.user = "monitor";
        job.uid = uid;
        job.email = null;
        job.os = parent.detail.os;

        job.showName = show;
        job.facilityName = facility;
        job.deptName = parent.detail.deptName;

        BuildableJob postJob = new BuildableJob(job);
        return postJob;
    }

    public Document getDoc() {
        return doc;
    }

    public List<BuildableDependency> getDepends() {
        return depends;
    }

    public List<BuildableJob> getJobs() {
        return jobs;
    }

    public String getShot() {
        return shot;
    }

    public String getShow() {
        return show;
    }

    public Optional<Integer> getUid() {
        return uid;
    }

    public String getUser() {
        return user;
    }

    public ServiceManager getServiceManager() {
        return serviceManager;
    }

    public void setServiceManager(ServiceManager serviceManager) {
        this.serviceManager = serviceManager;
    }
}

