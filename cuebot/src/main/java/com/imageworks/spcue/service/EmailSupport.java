
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

import java.io.ByteArrayOutputStream;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.io.StringWriter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Properties;

import org.apache.log4j.Logger;
import org.apache.velocity.Template;
import org.apache.velocity.VelocityContext;
import org.apache.velocity.app.VelocityEngine;
import org.jdom.output.Format;
import org.jdom.output.XMLOutputter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mail.MailException;
import org.springframework.mail.MailSender;
import org.springframework.mail.SimpleMailMessage;

import com.imageworks.spcue.BuildableJob;
import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.ExecutionSummary;
import com.imageworks.spcue.FrameStateTotals;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LayerStats;
import com.imageworks.spcue.SpcueRuntimeException;
import com.imageworks.spcue.grpc.job.LayerType;
import com.imageworks.spcue.util.CueExceptionUtil;
import com.imageworks.spcue.util.CueUtil;
import org.springframework.stereotype.Component;

@Component
public class EmailSupport {

    @Autowired
    private MailSender mailSender;

    @Autowired
    private JobManager jobManager;

    private Properties opencueProperties;

    private final Map<String, byte[]> imageMap;

    private static final Logger logger = Logger.getLogger(EmailSupport.class);

    public EmailSupport() {

        /*
         * The OpenCue configuration file which we need to find the email template.
         */
        opencueProperties = getOpenCueProperties();

        Map<String, byte[]> map = new HashMap<String, byte[]>();

        loadImage(map, "bar.png");
        loadImage(map, "opencue.png");
        loadImage(map, "fail.png");
        loadImage(map, "frame.png");
        loadImage(map, "graph_bar.png");
        loadImage(map, "header.png");
        loadImage(map, "html_bg.png");
        loadImage(map, "logo.png");
        loadImage(map, "memory.png");
        loadImage(map, "play.png");
        loadImage(map, "success.png");
        loadImage(map, "services/comp.png");
        loadImage(map, "services/default.png");
        loadImage(map, "services/ginsu.png");
        loadImage(map, "services/houdini.png");
        loadImage(map, "services/katana.png");
        loadImage(map, "services/maya.png");
        loadImage(map, "services/mentalray.png");
        loadImage(map, "services/nuke.png");
        loadImage(map, "services/playblast.png");
        loadImage(map, "services/prman.png");
        loadImage(map, "services/shell.png");
        loadImage(map, "services/simulation.png");
        loadImage(map, "services/svea.png");
        loadImage(map, "services/trinity.png");

        imageMap = Collections.unmodifiableMap(map);
    }

    private static void loadImage(Map<String, byte[]> map, String path) {
        InputStream is = null;
        ByteArrayOutputStream os = null;
        try {
            // Try loading as classpath resource
            is = EmailSupport.class.getResourceAsStream("/public/" + path);

            // Try loading as file (sbt-pack layout)
            if (is == null) {
                try {
                    is = new FileInputStream("public/" + path);
                } catch (FileNotFoundException fnfe) {
                    // do nothing
                }
            }

            // Try loading as file (unit tests don't have image paths loaded into classpath)
            if (is == null) {
                try {
                    is = new FileInputStream("conf/webapp/html/" + path);
                } catch (FileNotFoundException fnfe) {
                    // do nothing
                }
            }

            // If neither loaded, throw an exception
            if (is == null) {
                throw new IOException("Unable to load");
            }

            // Read contents to byte array
            os = new ByteArrayOutputStream();
            byte[] buffer = new byte[1024];
            int len;
            while ((len = is.read(buffer)) != -1) {
                os.write(buffer, 0, len);
            }
            byte[] data = os.toByteArray();

            // Put in map
            map.put(path, data);
        } catch (IOException ioe) {
            logger.error("Unable to read " + path, ioe);
        } finally {

            // Close streams
            if (os != null) {
                try {
                    os.close();
                } catch (IOException ioe) {
                    logger.error("Unable to close buffer for " + path, ioe);
                }
            }
            if (is != null) {
                try {
                    is.close();
                } catch (IOException ioe) {
                    logger.error("Unable to load " + path, ioe);
                }
            }
        }
    }

    public void reportLaunchError(JobSpec spec, Throwable t) {

        SimpleMailMessage msg = new SimpleMailMessage();
        msg.setTo(String.format("%s@imageworks.com", spec.getUser()));
        msg.setFrom("middle-tier@imageworks.com");
        msg.setCc("middle-tier@imageworks.com");
        msg.setSubject("Failed to launch OpenCue job.");

        StringBuilder sb = new StringBuilder(131072);
        sb.append("This is an automatic message from cuebot that is sent");
        sb.append(" after a queued\njob has failed to launch. This usually");
        sb.append(" occurs if you have made a mistake\nediting an outline");
        sb.append(" script. If you have no idea why you are receiving\nthis");
        sb.append(" message and your jobs are not hitting the cue, please");
        sb.append(" open a\nhelpdesk ticket with the debugging information");
        sb.append(" provided below.\n\n");

        sb.append("Failed to launch jobs:\n");
        for (BuildableJob job: spec.getJobs()) {
            sb.append(job.detail.name);
            sb.append("\n");
        }
        sb.append("\n\n");
        sb.append(new XMLOutputter(
                Format.getPrettyFormat()).outputString(spec.getDoc()));
        sb.append("\n\n");
        sb.append(CueExceptionUtil.getStackTrace(t));

        String body = sb.toString();
        msg.setText(body);
        sendMessage(msg);
    }

    public void reportJobComment(JobInterface job, CommentDetail c, String[] emails) {

        SimpleMailMessage msg = new SimpleMailMessage();
        msg.setTo(emails);
        msg.setFrom("opencue-noreply@imageworks.com");
        msg.setSubject("New comment on " + job.getName());

        StringBuilder sb = new StringBuilder(8096);
        sb.append("Job: " + job.getName() + "\n");
        sb.append("User: " + c.user + "\n");
        sb.append("Subject: " + c.subject + "\n");
        sb.append("-----------------------------------------\n");
        sb.append(c.message);

        msg.setText(sb.toString());
        sendMessage(msg);
    }

    public void sendMessage(SimpleMailMessage message) {
        try {
            mailSender.send(message);
        } catch (MailException ex) {
            logger.warn("Failed to send launch failure email, " + ex.getMessage());
        }
    }

    public Properties getOpenCueProperties() {

        // get the input stream of the properties file
        InputStream in = EmailSupport.class.getClassLoader()
                .getResourceAsStream("opencue.properties");

        Properties props = new java.util.Properties();
        try {
            props.load(in);
        } catch (IOException e) {
            props = new Properties();
            props.setProperty( "resource.loader", "file" );
            props.setProperty("class.resource.loader.class",
                    "org.apache.velocity.runtime.resource.loader.FileResourceLoader" );
            props.setProperty("file.resource.loader.path", "/opt/opencue/webapps/spcue");
        }
        return props;
    }

    public void sendShutdownEmail(JobInterface job) {

        JobDetail d = jobManager.getJobDetail(job.getJobId());
        if (d.email == null ) { return; }

        try {

            VelocityEngine ve = new VelocityEngine();
            ve.setProperty("resource.loader", "class");
            ve.setProperty("class.resource.loader.class", "org.apache.velocity.runtime.resource.loader.ClasspathResourceLoader");
            ve.init();

            VelocityContext context = new VelocityContext();
            ExecutionSummary exj = jobManager.getExecutionSummary(job);
            FrameStateTotals jts = jobManager.getFrameStateTotals(job);

            context.put("jobName", d.name);
            context.put("deptName", d.deptName.toUpperCase());
            context.put("showName", d.showName.toUpperCase());
            context.put("shotName", d.shot.toUpperCase());
            context.put("totalFrames", String.format("%04d", jts.total));
            context.put("succeededFrames", String.format("%04d", jts.succeeded));
            context.put("failedFrames",  String.format("%04d", jts.dead + jts.eaten + jts.waiting));
            context.put("checkpointFrames",  String.format("%04d", jts.checkpoint));
            context.put("maxRSS", String.format(Locale.ROOT, "%.1fGB",
                    exj.highMemoryKb / 1024.0 / 1024.0));
            context.put("coreTime",  String.format(Locale.ROOT, "%.1f",
                    exj.coreTime / 3600.0));

            Template t = ve.getTemplate("/conf/webapp/html/email_template.html");

            List<LayerDetail> layers = jobManager.getLayerDetails(job);
            List<LayerStats> layerStats = new ArrayList<LayerStats>(layers.size());

            for (LayerDetail layer: layers)  {
                if (layer.type.equals(LayerType.RENDER)) {
                    LayerStats stats = new LayerStats();
                    stats.setDetail(layer);
                    stats.setExecutionSummary(jobManager.getExecutionSummary(layer));
                    stats.setFrameStateTotals(jobManager.getFrameStateTotals(layer));
                    stats.setThreadStats(jobManager.getThreadStats(layer));
                    stats.setOutputs(jobManager.getLayerOutputs(layer));
                    layerStats.add(stats);
                }
            }

            context.put("layers", layerStats);

            StringWriter w = new StringWriter();
            t.merge(context, w);

            String subject = "OpenCue Job " + d.getName();
            if (jts.total != jts.succeeded) {
                subject = "Failed " + subject;
            }
            else {
                subject = "Succeeded " + subject;
            }

            String from = "middle-tier@imageworks.com";
            for (String email : d.email.split(",")) {
                try {
                    CueUtil.sendmail(email, from, subject, new StringBuilder(w.toString()), imageMap);
                } catch (Exception e) {
                    // just log and eat if the mail server is down or something
                    // of that nature.
                    logger.info("Failed to send job complete mail, reason: " + e);
                }
            }
        }
        catch (Exception e) {
            e.printStackTrace();
            throw new SpcueRuntimeException("Failed " + e, e);
        }
    }
}

