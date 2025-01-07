
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

import java.io.*;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;
import org.apache.velocity.Template;
import org.apache.velocity.VelocityContext;
import org.apache.velocity.app.VelocityEngine;
import org.jdom.output.Format;
import org.jdom.output.XMLOutputter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
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

public class EmailSupport {

    private MailSender mailSender;
    private JobManager jobManager;
    private String emailDomain;
    private String emailFromAddress;
    private String[] emailCcAddresses;

    private Map<String, byte[]> imageMap;

    private static final Logger logger = LogManager.getLogger(EmailSupport.class);

    @Autowired
    public EmailSupport(Environment env) {
        this.emailDomain = env.getProperty("email.domain", "opencue.io");
        this.emailFromAddress = env.getProperty("email.from.address", "opencue-noreply@opencue.io");
        this.emailCcAddresses = env.getProperty("email.cc.addresses", "").split(",");
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
        msg.setTo(String.format("%s@%s", spec.getUser(), this.emailDomain));
        msg.setFrom(this.emailFromAddress);
        msg.setCc(this.emailCcAddresses);
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
        for (BuildableJob job : spec.getJobs()) {
            sb.append(job.detail.name);
            sb.append("\n");
        }
        sb.append("\n\n");
        sb.append(new XMLOutputter(Format.getPrettyFormat()).outputString(spec.getDoc()));
        sb.append("\n\n");
        sb.append(CueExceptionUtil.getStackTrace(t));

        String body = sb.toString();
        msg.setText(body);
        sendMessage(msg);
    }

    public void reportJobComment(JobInterface job, CommentDetail c, String[] emails) {

        SimpleMailMessage msg = new SimpleMailMessage();
        msg.setTo(emails);
        msg.setFrom(this.emailFromAddress);
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

    public void sendShutdownEmail(JobInterface job) {

        JobDetail d = jobManager.getJobDetail(job.getJobId());
        if (d.email == null) {
            return;
        }

        try {

            VelocityEngine ve = new VelocityEngine();
            ve.setProperty("resource.loader", "class");
            ve.setProperty("class.resource.loader.class",
                    "org.apache.velocity.runtime.resource.loader.ClasspathResourceLoader");
            ve.init();

            VelocityContext context = new VelocityContext();
            ExecutionSummary exj = jobManager.getExecutionSummary(job);
            FrameStateTotals jts = jobManager.getFrameStateTotals(job);

            String status = "";
            if (jts.total != jts.succeeded) {
                status = "Failed ";
            } else {
                status = "Succeeded ";
            }

            context.put("jobName", d.name);
            context.put("jobStatus", status.toUpperCase());
            context.put("deptName", d.deptName.toUpperCase());
            context.put("showName", d.showName.toUpperCase());
            context.put("totalLayers", d.totalLayers);
            context.put("shotName", d.shot.toUpperCase());
            context.put("succeededFrames", jts.succeeded);
            context.put("totalFrames", jts.total);
            context.put("dependFrames", jts.depend);
            context.put("deadFrames", jts.dead);
            context.put("waitingFrames", jts.waiting);
            context.put("eatenFrames", jts.eaten);
            context.put("failedFrames", jts.dead + jts.eaten + jts.waiting);
            context.put("checkpointFrames", jts.checkpoint);
            context.put("maxRSS",
                    String.format(Locale.ROOT, "%.1fGB", exj.highMemoryKb / 1024.0 / 1024.0));
            context.put("coreTime", String.format(Locale.ROOT, "%.1f", exj.coreTime / 3600.0));

            Template t = ve.getTemplate("/conf/webapp/html/email_template.html");

            List<LayerDetail> layers = jobManager.getLayerDetails(job);
            List<LayerStats> layerStats = new ArrayList<LayerStats>(layers.size());

            boolean shouldCreateFile = false;

            Map<String, byte[]> map = new HashMap<String, byte[]>();
            loadImage(map, "opencue_logo.png");

            for (LayerDetail layer : layers) {
                if (layer.type.equals(LayerType.RENDER)) {
                    LayerStats stats = new LayerStats();
                    stats.setDetail(layer);
                    stats.setExecutionSummary(jobManager.getExecutionSummary(layer));
                    stats.setFrameStateTotals(jobManager.getFrameStateTotals(layer));
                    stats.setThreadStats(jobManager.getThreadStats(layer));
                    stats.setOutputs(jobManager.getLayerOutputs(layer).stream().sorted()
                            .collect(Collectors.toList()));
                    layerStats.add(stats);
                    if (stats.getOutputs().size() > 3)
                        shouldCreateFile = true;
                    if (!layer.services.isEmpty())
                        loadImage(map, "services/" + layer.services.toArray()[0] + ".png");
                }
            }

            imageMap = Collections.unmodifiableMap(map);

            context.put("layers", layerStats);

            StringWriter w = new StringWriter();
            t.merge(context, w);

            String subject = "OpenCue Job " + d.getName();

            subject = status + subject;

            BufferedWriter output = null;
            File file = null;
            if (shouldCreateFile) {
                try {
                    file = new File("my_outputs.txt");
                    output = new BufferedWriter(new FileWriter(file));
                    for (LayerDetail layer : layers) {
                        if (layer.type.equals(LayerType.RENDER)) {
                            List<String> sortedNames = jobManager.getLayerOutputs(layer).stream()
                                    .sorted().collect(Collectors.toList());
                            output.write(layer.name + "\n" + String.join("\n", sortedNames) + "\n");
                        }
                    }
                } catch (IOException e) {
                    e.printStackTrace();
                } finally {
                    if (output != null) {
                        try {
                            output.close();
                        } catch (IOException e) {
                            e.printStackTrace();
                        }
                    }
                }
            }

            for (String email : d.email.split(",")) {
                try {
                    CueUtil.sendmail(email, this.emailFromAddress, subject,
                            new StringBuilder(w.toString()), imageMap, file);
                } catch (Exception e) {
                    // just log and eat if the mail server is down or something
                    // of that nature.
                    logger.info("Failed to send job complete mail, reason: " + e);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
            throw new SpcueRuntimeException("Failed " + e, e);
        }
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public void setMailSender(MailSender mailSender) {
        this.mailSender = mailSender;
    }
}
