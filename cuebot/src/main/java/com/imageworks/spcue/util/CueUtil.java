
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



package com.imageworks.spcue.util;

import java.lang.management.ManagementFactory;
import java.lang.management.ThreadMXBean;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Collections;
import java.util.Date;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Properties;
import java.util.Set;
import java.util.regex.Pattern;
import javax.activation.DataHandler;
import javax.activation.DataSource;
import javax.mail.BodyPart;
import javax.mail.Message;
import javax.mail.Session;
import javax.mail.Transport;
import javax.mail.internet.InternetAddress;
import javax.mail.internet.MimeBodyPart;
import javax.mail.internet.MimeMessage;
import javax.mail.internet.MimeMultipart;
import javax.mail.util.ByteArrayDataSource;

import org.apache.log4j.Logger;

import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.SpcueRuntimeException;
import com.imageworks.spcue.dispatcher.Dispatcher;

/**
 * CueUtil is set of common methods used throughout the application.
 */
public final class CueUtil {

    private static final Logger logger = Logger.getLogger(CueUtil.class);

    /**
     * Commonly used macros for gigabyte values in KB.
     */
    public static final long MB128 = 131072;
    public static final long MB256 = 262144;
    public static final long MB512 = 524288;
    public static final long GB = 1048576;
    public static final long GB2 = 1048576L * 2;
    public static final long GB4 = 1048576L * 4;
    public static final long GB8 = 1048576L * 8;
    public static final long GB16 = 1048576L * 16;
    public static final long GB32 = 1048576L * 32;

    /**
     * Features that relay on an integer greated than 0 to work
     * properly are disabled by setting them to -1.
     */
    public static final int FEATURE_DISABLED = -1;

    /**
     * A const to repesent a single core
     */
    public static final int ONE_CORE = 100;

    /**
     * One hour of time in seconds.
     */
    public static final int ONE_HOUR = 3600;

    /**
     * Return true if the given name is formatted as a valid
     * allocation name.  Allocation names should be facility.unique_name.
     *
     * @param name
     * @return
     */
    public static boolean verifyAllocationNameFormat(String name) {
        return Pattern.matches("^(\\w+)\\.(\\w+)$", name);
    }

    /**
     * Split an allocation name and return its parts in a
     * String array. The first element is the facility, the second
     * is the allocation's unique name.
     *
     * @param name
     * @return
     */
    public static String[] splitAllocationName(String name) {
        String[] parts = name.split("\\.", 2);
        if (parts.length != 2 || !verifyAllocationNameFormat(name)) {
            throw new SpcueRuntimeException(
                    "Allocation names must be in the form of facility.alloc. The name " +
                    name + " is not valid.");
        }
        return parts;
    }
    /**
     * Finds the chunk that the dependErFrame belongs to in the
     * given sequence of frames.
     *
     * @param dependOnFrames - the full frame range to depend on
     * @param dependErFrame - the dependent frame number.
     * @return
     */
    public static int findChunk(List<Integer> dependOnFrames, int dependErFrame) {
        int dependOnFrame = -1;
        if (dependOnFrames.contains(dependErFrame)) {
            dependOnFrame = dependErFrame;
        } else {
            int size = dependOnFrames.size();
            for (int i=0; i < size; i++) {
                dependOnFrame = dependOnFrames.get(i);
                if (dependOnFrame > dependErFrame) {
                    dependOnFrame = dependOnFrames.get(i-1);
                    break;
                }
            }
        }

        if (dependOnFrame == -1) {
            throw new RuntimeException("unable to find chunk for frame: " + dependErFrame +
                    " in the range: " + dependOnFrames.toString());
        }
        return dependOnFrame;
    }
    /**
     * A simple send mail method
     *
     * @param to
     * @param from
     * @param subject
     * @param body
     * @param images
     */
    public static void sendmail(String to, String from, String subject, StringBuilder body, Map<String, byte[]> images) {
        try {
            Properties props = System.getProperties();
            props.put("mail.smtp.host", "smtp");
            Session session = Session.getDefaultInstance(props, null);
            Message msg = new MimeMessage(session);
            msg.setFrom(new InternetAddress(from));
            msg.setReplyTo(new InternetAddress[] { new InternetAddress(from) } );
            msg.setRecipients(Message.RecipientType.TO,
              InternetAddress.parse(to, false));
            msg.setSubject(subject);

            MimeMultipart mimeMultipart = new MimeMultipart();
            mimeMultipart.setSubType("alternative");

            BodyPart htmlBodyPart = new MimeBodyPart();
            htmlBodyPart.setContent(body.toString(), "text/html");
            mimeMultipart.addBodyPart(htmlBodyPart);

            for (Entry<String, byte[]> e : images.entrySet()) {
                String name = e.getKey().replace('/', '_');

                BodyPart imageBodyPart = new MimeBodyPart();
                DataSource ds = new ByteArrayDataSource(e.getValue(), "image/png");
                DataHandler dh = new DataHandler(ds);
                imageBodyPart.setDataHandler(dh);
                imageBodyPart.setFileName(name);
                imageBodyPart.setDisposition("inline");
                imageBodyPart.setHeader("Content-ID", '<' + name + '>');
                mimeMultipart.addBodyPart(imageBodyPart);
            }

            msg.setContent(mimeMultipart);
            msg.setHeader("X-Mailer", "OpenCueMailer");
            msg.setSentDate(new Date());
            Transport.send(msg);
        }
        catch (Exception e) {
            throw new RuntimeException("failed to send email: " + e);
        }
    }

    public static final String formatDuration(long seconds) {
        return String.format("%02d:%02d:%02d",seconds / 3600,(seconds % 3600) / 60,seconds % 60);
    }

    public static final String formatDuration(int seconds) {
        return String.format("%02d:%02d:%02d",seconds / 3600,(seconds % 3600) / 60,seconds % 60);
    }

    public static final String KbToMb(long kb) {
        return String.format("%dMB", kb / 1024);
    }

    public static final long convertKbToFakeKb64bit(long Kb) {
        return (long) (Math.ceil((Kb * 0.0009765625) * 0.0009765625) * 1048576) - Dispatcher.MEM_RESERVED_SYSTEM;
    }

    public static final long convertKbToFakeKb32bit(long Kb) {
        return (long) (Math.floor((Kb * 0.0009765625) * 0.0009765625) * 1048576) - Dispatcher.MEM_RESERVED_SYSTEM;
    }

    /**
     * returns epoch time
     *
     * @return int
     */
    public static int getTime() {
        return (int) (System.currentTimeMillis() / 1000);
    }

    /**
     * returns a frame name from a layer and frame number.
     *
     * @param layer
     * @param num
     * @return String
     */
    public final static String buildFrameName(LayerInterface layer, int num) {
        return String.format("%04d-%s", num, layer.getName());
    }

    public final static String buildProcName(String host, int cores, int gpus) {
        return String.format(Locale.ROOT, "%s/%4.2f/%d", host, Convert.coreUnitsToCores(cores), gpus);
    }

    /**
     * for logging how long an operation took
     *
     * @param time
     * @param message
     */
    public final static void logDuration(long time, String message) {
        long duration = System.currentTimeMillis() - time;
        logger.info("Operation: " + message + " took " + duration + "ms");
    }

    /**
     * return the milliseconds since time
     *
     * @param time
     */
    public final static long duration(long time) {
        return System.currentTimeMillis() - time;
    }

    public static final long getCpuUsage() {
        ThreadMXBean mx = ManagementFactory.getThreadMXBean();
        mx.setThreadCpuTimeEnabled(true);
        long result = 0;
        for (long id: mx.getAllThreadIds()) {
            result = result + mx.getThreadUserTime(id);
        }
        return result;
    }

    private static final int DAY_START = 7;
    private static final int DAY_END = 19;
    public static boolean isDayTime() {
        Calendar cal = Calendar.getInstance();
        int hour_of_day = cal.get(Calendar.HOUR_OF_DAY);
        if (hour_of_day >= DAY_START && hour_of_day < DAY_END) {
            return true;
        }
        return false;
    }

    /**
     * Take a frame range and chunk size and return an
     * ordered array of frames with all duplicates removed.
     *
     * @param range
     * @param chunkSize
     * @return
     */
    public static List<Integer> normalizeFrameRange(String range, int chunkSize) {
        return normalizeFrameRange(new FrameSet(range), chunkSize);
    }

    /**
     * Take a frame range and chunk size and return an
     * ordered array of frames with all duplicates removed.
     *
     * @param frameSet
     * @param chunkSize
     * @return
     */
    public static List<Integer> normalizeFrameRange(FrameSet frameSet, int chunkSize) {

        int rangeSize = frameSet.size();
        Set<Integer> result = new LinkedHashSet<Integer>(rangeSize / chunkSize);

        /**
         * Have to remove all duplicates and maintain order before chunking it.
         */
        if (chunkSize > 1) {

            /**
             * This handles people who chunk on 1,000,000.
             */
            if (chunkSize > rangeSize) {
                result.add(frameSet.get(0));
            }
            else {

                /**
                 * A linked hash set to weed out duplicates
                 * but maintain frame ordering.
                 */
                final Set<Integer> tempResult =
                    new LinkedHashSet<Integer>((rangeSize / chunkSize) + 1);

                for (int idx = 0; idx < rangeSize; idx = idx + 1) {
                    tempResult.add(frameSet.get(idx));
                }

                /**
                 * Now go through the frames and add 1 frame
                 * for every chunk.
                 */
                int idx = 0;
                for (int frame: tempResult) {
                    if (idx % chunkSize == 0) {
                        result.add(frame);
                    }
                    idx = idx + 1;
                }
            }
        }
        else {
            for (int idx = 0; idx < rangeSize; idx = idx + 1) {
                result.add(frameSet.get(idx));
            }
        }

        return Collections.unmodifiableList(
                new ArrayList<Integer>(result));
    }
}

