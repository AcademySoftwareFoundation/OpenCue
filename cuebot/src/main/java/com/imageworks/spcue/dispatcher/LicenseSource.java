
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

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * Live view of floating application licenses (Houdini Engine, Katana, Maya, ...) for the planner.
 *
 * <h2>Why this exists</h2> A {@code limit_record} holds a static number an admin typed. That works
 * for an internal throttle but not for a real license pool, because the pool is also drawn on from
 * outside the cue: artist workstations, CI, other farms. A fixed cap of 100 means nothing when 60
 * seats are already out to people. The only authority on how many seats are free is the license
 * server, so this class polls it and the planner gates against the live number.
 *
 * <h2>Shape</h2> A background daemon thread asks a site-provided endpoint for every license we care
 * about and keeps the answer in memory. The planner never touches the endpoint on the hot path:
 * once per tick it asks for {@link #snapshotBudgets} and gets plain numbers. The provider is either
 * an {@code http://} endpoint or {@code script:<cmd>} wrapping a vendor CLI such as
 * {@code sesictrl}; either way it returns the same JSON:
 *
 * <pre>
 * {"queried_at": 1690000000,
 *  "licenses": [{"name": "hengine", "feature": "Houdini Engine", "total": 800,
 *                "available": 794, "host_based": false,
 *                "hosts": [{"host": "wolf1018", "count": 1}]}]}
 * </pre>
 *
 * {@code available} is server truth and has already netted out every consumer, ours included.
 * {@code queried_at} (epoch seconds, when the numbers were true) is REQUIRED: a response without a
 * usable timestamp is rejected and the previous sample keeps aging toward stale, because a provider
 * re-serving a cached payload with no timestamp would otherwise look fresh forever. {@code hosts}
 * is optional; when present it enables seat counting for host-based licenses and shows which render
 * nodes are dual-used as workstations.
 *
 * <h2>Staleness is the whole difficulty</h2> The planner always acts on a sample that is already
 * old, and between the sample and a real checkout seats move. Two terms correct for that:
 *
 * <ul>
 * <li><b>in-flight</b>: frames WE booked since the sample was taken. The server has not seen them
 * yet, so they are not in {@code available} and must be subtracted, otherwise one tick happily
 * books fifty frames against ten free seats. It is derived from the database rather than from a
 * counter in this process, so a Cuebot that takes over after a failover computes the same number as
 * the one it replaced.</li>
 * <li><b>headroom</b>: seats deliberately left for interactive users, per license.</li>
 * </ul>
 *
 * When the sample goes older than {@code stale_seconds} this fails CLOSED: budgets go to zero and
 * licensed layers stop being placed. Over-booking a license we cannot see would fail frames on
 * checkout on the farm; holding them costs throughput on licensed layers only, and is recoverable.
 *
 * <h2>Every Cuebot polls</h2> Not just the planning leader. The poll is a cheap read and it keeps
 * standbys warm, so a Cuebot promoted by failover already holds a fresh sample instead of gating
 * all licensed work until its first poll lands.
 */
public class LicenseSource {

    private static final Logger logger = LogManager.getLogger(LicenseSource.class);

    /** Cap on a provider response, so a broken endpoint cannot exhaust the heap. */
    private static final int MAX_RESPONSE_BYTES = 4 * 1024 * 1024;

    private final Environment env;
    private final JdbcTemplate jdbc;

    private final String provider;
    private final String envKey;
    private final int pollSeconds;
    private final int timeoutSeconds;
    private final int staleSeconds;
    private final int defaultHeadroom;
    private final int inflightPadSeconds;

    private volatile Thread poller;
    private volatile boolean running;

    /** Last good sample, or null before the first successful poll. */
    private volatile Sample sample = null;

    /** Consecutive failed polls; drives the log-once-then-quiet warning. */
    private volatile int consecutiveFailures = 0;

    /** Throttle for the "holding licensed layers" warning, which is per tick otherwise. */
    private static final long STALE_WARN_INTERVAL_MS = 60_000;
    private volatile long lastStaleWarnMs = 0;
    private volatile long lastNoProviderWarnMs = 0;

    public LicenseSource(Environment env, JdbcTemplate jdbc) {
        this.env = env;
        this.jdbc = jdbc;
        // Trimmed: a properties file with a trailing space would otherwise count as
        // "configured" and start a poller that fails forever, reporting a parse
        // error instead of the truth, which is that nobody set a provider.
        this.provider = env.getProperty("scheduler.license.provider", "").trim();
        this.envKey = env.getProperty("scheduler.license.env_key", "CUE_LICENSES");
        this.pollSeconds = env.getProperty("scheduler.license.poll_seconds", Integer.class, 20);
        this.timeoutSeconds =
                env.getProperty("scheduler.license.timeout_seconds", Integer.class, 10);
        this.staleSeconds = env.getProperty("scheduler.license.stale_seconds", Integer.class, 300);
        this.defaultHeadroom =
                env.getProperty("scheduler.license.headroom.default", Integer.class, 0);
        this.inflightPadSeconds =
                env.getProperty("scheduler.license.inflight_pad_seconds", Integer.class, 5);
    }

    /**
     * Is a provider configured, i.e. can we obtain live numbers at all?
     *
     * There is deliberately NO separate on/off switch. What turns licensing on is a layer asking
     * for a license, because that is a hard requirement of the work, not a site preference: a flag
     * that had to be remembered would sooner or later be forgotten, and the farm would then quietly
     * book straight through a license pool. If no provider is configured and a layer asks for a
     * license anyway, that layer is HELD rather than run blind (see {@link #snapshotBudgets}).
     */
    public boolean hasProvider() {
        return !provider.isEmpty();
    }

    /** The layer environment key that binds a layer to its licenses, e.g. {@code CUE_LICENSES}. */
    public String getEnvKey() {
        return envKey;
    }

    // ---- lifecycle --------------------------------------------------------

    /**
     * Start the background poll. Polls once immediately (in the new thread, so startup is never
     * blocked by a slow license server) and then every {@code poll_seconds}. Until that first
     * sample lands, licensed layers are held: no sample means no authority to book.
     */
    public synchronized void start() {
        if (!hasProvider() || poller != null)
            return;
        running = true;
        Thread t = new Thread(() -> {
            while (running) {
                try {
                    poll();
                } catch (RuntimeException e) {
                    logger.warn("LicenseSource: poll failed: " + e);
                }
                try {
                    Thread.sleep(1000L * pollSeconds);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    return;
                }
            }
        });
        t.setName("Scheduler-license-poll");
        t.setDaemon(true);
        poller = t;
        t.start();
        logger.info("LicenseSource: polling " + provider + " every " + pollSeconds + "s"
                + " (env key " + envKey + ", stale after " + staleSeconds + "s)");
    }

    public synchronized void stop() {
        running = false;
        Thread t = poller;
        poller = null;
        if (t != null)
            t.interrupt();
    }

    // ---- the sample ------------------------------------------------------

    /** One license as the provider reported it. */
    public static final class LicenseState {
        public final String name;
        public final String feature;
        public final int total;
        public final int available;
        public final boolean hostBased;
        /** Hosts the provider says hold this license (any consumer, not just ours). Never null. */
        public final Set<String> hosts;

        LicenseState(String name, String feature, int total, int available, boolean hostBased,
                Set<String> hosts) {
            this.name = name;
            this.feature = feature;
            this.total = total;
            this.available = available;
            this.hostBased = hostBased;
            this.hosts = hosts;
        }
    }

    /**
     * A provider response plus the two clock facts needed to age it: when we received it, and how
     * old it already was on arrival ({@code lagSeconds}, from the provider's own
     * {@code queried_at}).
     */
    private static final class Sample {
        final Map<String, LicenseState> licenses;
        final long receivedAtMs;
        final long lagSeconds;

        Sample(Map<String, LicenseState> licenses, long receivedAtMs, long lagSeconds) {
            this.licenses = licenses;
            this.receivedAtMs = receivedAtMs;
            this.lagSeconds = lagSeconds;
        }
    }

    /**
     * What the planner may book for one license this tick.
     *
     * For a floating license only {@link #usable} matters: frames still bookable right now. For a
     * host-based license the cap counts distinct hosts, so the planner needs the seat set
     * ({@link #seats}, hosts that already hold one, including workstations outside the cue) and
     * {@link #seatCap}, the most seats it may let exist.
     */
    public static final class LicenseBudget {
        public final String name;
        public final boolean hostBased;
        public final int usable;
        public final int seatCap;
        public final Set<String> seats;
        /** Sample too old (or missing) to act on: everything is held. */
        public final boolean stale;

        LicenseBudget(String name, boolean hostBased, int usable, int seatCap, Set<String> seats,
                boolean stale) {
            this.name = name;
            this.hostBased = hostBased;
            this.usable = usable;
            this.seatCap = seatCap;
            this.seats = seats;
            this.stale = stale;
        }
    }

    // ---- per-tick read ---------------------------------------------------


    /**
     * Per-license budgets for this tick: {@code available - in-flight - headroom} for floating
     * licenses, and the seat set plus seat cap for host-based ones.
     *
     * Returns an empty map when licensing is off. When the sample is missing or stale every license
     * the planner asks about comes back {@code stale}, which holds licensed layers rather than
     * guessing.
     *
     * @param wanted license names the current candidate set actually needs; nothing else is
     *        computed.
     */
    public Map<String, LicenseBudget> snapshotBudgets(Set<String> wanted) {
        if (wanted.isEmpty())
            return Collections.emptyMap();
        if (!hasProvider()) {
            // A layer asked for a license and this Cuebot has no way to find out
            // how many are free. Hold it: running it blind would book straight
            // through somebody's license pool. Loud, because it is a
            // misconfiguration, not a transient condition.
            long nowMs = System.currentTimeMillis();
            if (nowMs - lastNoProviderWarnMs > STALE_WARN_INTERVAL_MS) {
                lastNoProviderWarnMs = nowMs;
                logger.warn("LicenseSource: layers ask for licenses " + wanted
                        + " but scheduler.license.provider is not configured;"
                        + " holding that work. Configure a provider or remove" + " " + envKey
                        + " from those layers.");
            }
            Map<String, LicenseBudget> held = new HashMap<>();
            for (String name : wanted)
                held.put(name, new LicenseBudget(name, false, 0, 0, Collections.emptySet(), true));
            return held;
        }

        Sample s = sample;
        long ageSeconds = (s == null) ? Long.MAX_VALUE
                : s.lagSeconds + (System.currentTimeMillis() - s.receivedAtMs) / 1000L;
        boolean stale = (s == null) || ageSeconds > staleSeconds;

        Map<String, LicenseBudget> out = new HashMap<>();
        if (stale) {
            // Throttled: this fires per tick while a provider is down, which is
            // once every few seconds on every Cuebot. One line a minute is enough
            // to see the outage without burying the log that would explain it.
            long nowMs = System.currentTimeMillis();
            if ((s != null || consecutiveFailures > 0)
                    && nowMs - lastStaleWarnMs > STALE_WARN_INTERVAL_MS) {
                lastStaleWarnMs = nowMs;
                logger.warn("LicenseSource: "
                        + (s == null ? "no sample yet from " + provider
                                : "sample is " + ageSeconds + "s old, stale after " + staleSeconds
                                        + "s")
                        + "; holding licensed layers (" + wanted.size() + " pool(s))");
            }
            for (String name : wanted) {
                out.put(name, new LicenseBudget(name, false, 0, 0, Collections.emptySet(), true));
            }
            return out;
        }

        // In-flight: what we booked since the sample was taken, so it is not yet
        // reflected in `available`. Ask the DB for it (any Cuebot then agrees) and
        // ask by AGE rather than by absolute instant, so a clock offset between
        // Cuebot and Postgres cannot skew the window.
        //
        // The window is padded, because a provider's timestamp is only as honest
        // as the provider. Collecting the numbers takes time (a vendor CLI, a
        // query, an exporter scrape), and one that stamps the result when it
        // FINISHES advertises a sample fresher than it is. Frames we booked during
        // that collection then fall outside the window and outside `available`,
        // and go uncounted twice over, which is exactly how a tick over-books.
        // Widening the window can only over-count in-flight, whose consequence is
        // booking slightly less; getting it wrong the other way fails frames at
        // checkout on the farm.
        InFlight inFlight = readInFlight(ageSeconds + inflightPadSeconds, wanted);

        for (String name : wanted) {
            LicenseState st = s.licenses.get(name);
            if (st == null) {
                // The layer asks for a license the provider does not report. We
                // have no authority on it, so hold rather than assume it is free.
                logger.warn("LicenseSource: no data for license '" + name
                        + "' requested by a layer; holding its frames");
                out.put(name, new LicenseBudget(name, false, 0, 0, Collections.emptySet(), true));
                continue;
            }
            int headroom = env.getProperty("scheduler.license.headroom." + name, Integer.class,
                    defaultHeadroom);
            if (st.hostBased) {
                // Machines already holding this license: the ones the provider
                // reports, UNION every host of ours currently running it. The
                // union never double counts a dual-use machine, and a frame
                // placed on any of them is free, because it shares that
                // machine's one checkout.
                Set<String> seats = new HashSet<>(st.hosts);
                seats.addAll(inFlight.hostsByLicense.getOrDefault(name, Collections.emptySet()));
                // How many machines may hold this license in total.
                //
                // Bounded via `available` rather than total - headroom, because
                // `hosts` is optional: a provider that reports none leaves us
                // blind to the machines outside the cue holding seats, and
                // capping at total - headroom would then let us open every seat
                // the license has while artists already hold some. `available` is
                // server truth and has those holders netted out.
                //
                // The subtraction of hostsRecent is what makes it STABLE. seats is
                // current while `available` is from the sample, so adding the two
                // alone would count our own growth twice: every machine we seated
                // since the sample would raise the cap by one and immediately
                // justify another. Netting out the machines seated inside the
                // sample window removes that feedback, exactly as the in-flight
                // frame count does for a floating license.
                //
                // When the provider DOES report hosts the terms cancel to
                // total - headroom, so one expression covers both cases.
                int recentHosts = inFlight.recentHostsByLicense
                        .getOrDefault(name, Collections.emptySet()).size();
                int seatCap = seats.size() + Math.max(0, st.available - headroom - recentHosts);
                out.put(name, new LicenseBudget(name, true, 0, seatCap, seats, false));
            } else {
                int booked = inFlight.framesByLicense.getOrDefault(name, 0);
                int usable = st.available - booked - headroom;
                if (usable < 0)
                    usable = 0;
                out.put(name,
                        new LicenseBudget(name, false, usable, 0, Collections.emptySet(), false));
            }
        }
        return out;
    }

    /**
     * Frames booked since the sample (floating), and hosts running licensed frames (host-based).
     */
    private static final class InFlight {
        final Map<String, Integer> framesByLicense = new HashMap<>();
        final Map<String, Set<String>> hostsByLicense = new HashMap<>();
        /** Hosts that started running the license INSIDE the sample window. */
        final Map<String, Set<String>> recentHostsByLicense = new HashMap<>();
    }

    /**
     * The in-flight terms, from the database so every Cuebot derives the same numbers.
     *
     * Two different windows, because the two license kinds count different things:
     * <ul>
     * <li>floating: frames started WITHIN the sample's age, exactly the bookings the license
     * server has not observed yet.</li>
     * <li>host-based: ALL hosts currently running the license, any age. Seats are a set, so
     * unioning our full host list with the provider's is idempotent and covers providers that
     * report no hosts at all.</li>
     * </ul>
     */
    private InFlight readInFlight(long ageSeconds, Set<String> wanted) {
        InFlight f = new InFlight();
        // One pass over running licensed frames. Driven from layer_env (indexed on
        // the key) so a farm whose licensed layers are a small slice of the whole
        // does not pay for the rest.
        jdbc.query("SELECT le.str_value AS lic, f.str_host AS host, "
                + "  (f.ts_started > now() - CAST(? AS INTERVAL)) AS recent " + "FROM layer_env le "
                + "JOIN frame f ON f.pk_layer = le.pk_layer "
                + "WHERE le.str_key = ? AND f.str_state = 'RUNNING'", rs -> {
                    boolean recent = rs.getBoolean("recent");
                    String host = rs.getString("host");
                    for (String name : splitNames(rs.getString("lic"))) {
                        if (!wanted.contains(name))
                            continue;
                        if (recent)
                            f.framesByLicense.merge(name, 1, Integer::sum);
                        if (host != null && !host.isEmpty()) {
                            String h = host.toLowerCase();
                            f.hostsByLicense.computeIfAbsent(name, k -> new HashSet<>()).add(h);
                            if (recent) {
                                f.recentHostsByLicense.computeIfAbsent(name, k -> new HashSet<>())
                                        .add(h);
                            }
                        }
                    }
                }, ageSeconds + " seconds", envKey);
        return f;
    }

    // ---- polling ---------------------------------------------------------

    /** Fetch and parse one sample. Keeps the previous sample on failure (staleness handles it). */
    void poll() {
        long t0 = System.currentTimeMillis();
        String body;
        try {
            body = fetch();
        } catch (Exception e) {
            consecutiveFailures++;
            if (consecutiveFailures == 1 || consecutiveFailures % 10 == 0) {
                logger.warn("LicenseSource: provider " + provider + " failed ("
                        + consecutiveFailures + " in a row): " + e);
            }
            return;
        }
        try {
            JsonObject root = JsonParser.parseString(body).getAsJsonObject();
            Map<String, LicenseState> parsed = new HashMap<>();
            JsonArray arr = root.getAsJsonArray("licenses");
            if (arr != null) {
                for (JsonElement el : arr) {
                    JsonObject o = el.getAsJsonObject();
                    String name = str(o, "name", null);
                    if (name == null || name.isEmpty())
                        continue;
                    Set<String> hosts = new HashSet<>();
                    JsonArray ha = o.getAsJsonArray("hosts");
                    if (ha != null) {
                        for (JsonElement he : ha) {
                            String h = he.isJsonObject() ? str(he.getAsJsonObject(), "host", null)
                                    : he.getAsString();
                            if (h != null && !h.isEmpty())
                                hosts.add(h.toLowerCase());
                        }
                    }
                    parsed.put(name.toLowerCase(),
                            new LicenseState(name.toLowerCase(), str(o, "feature", name),
                                    num(o, "total", 0), num(o, "available", 0),
                                    bool(o, "host_based", false), hosts));
                }
            }
            long queriedAt = lng(root, "queried_at", 0L);
            long now = System.currentTimeMillis();
            // queried_at is REQUIRED: without it a provider re-serving a stale
            // cached payload would look fresh forever. Reject the poll and let
            // the previous sample keep aging toward stale (fail closed).
            if (queriedAt <= 0L) {
                consecutiveFailures++;
                if (consecutiveFailures == 1 || consecutiveFailures % 10 == 0) {
                    logger.warn("LicenseSource: provider response has no usable queried_at "
                            + "(got " + queriedAt + "); rejecting sample (" + consecutiveFailures
                            + " in a row)");
                }
                return;
            }
            // How stale the sample already was when it reached us. Clamped at 0:
            // a provider clock running ahead must not make a sample look fresher
            // than it is.
            long lag = Math.max(0L, now / 1000L - queriedAt);
            sample = new Sample(parsed, now, lag);
            if (consecutiveFailures > 0) {
                logger.info("LicenseSource: provider recovered after " + consecutiveFailures
                        + " failed polls");
            }
            consecutiveFailures = 0;
            if (logger.isDebugEnabled()) {
                StringBuilder sb = new StringBuilder();
                for (LicenseState st : parsed.values()) {
                    sb.append(' ').append(st.name).append('=').append(st.available).append('/')
                            .append(st.total);
                    if (st.hostBased)
                        sb.append("(hosts:").append(st.hosts.size()).append(')');
                }
                logger.debug(
                        "LicenseSource: sample in " + (now - t0) + "ms, lag " + lag + "s:" + sb);
            }
        } catch (RuntimeException e) {
            consecutiveFailures++;
            logger.warn("LicenseSource: unparseable provider response: " + e);
        }
    }

    /** {@code http:URL} or {@code script:/path [args]}. */
    private String fetch() throws IOException, InterruptedException {
        if (provider.startsWith("http:") || provider.startsWith("https:")) {
            return fetchHttp(provider);
        }
        if (provider.startsWith("script:")) {
            return fetchScript(provider.substring("script:".length()).trim());
        }
        throw new IOException(
                "provider must start with http:, https: or script: (got " + provider + ")");
    }

    private String fetchHttp(String url) throws IOException {
        HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
        conn.setConnectTimeout(timeoutSeconds * 1000);
        conn.setReadTimeout(timeoutSeconds * 1000);
        conn.setRequestProperty("Accept", "application/json");
        try {
            int code = conn.getResponseCode();
            if (code != 200)
                throw new IOException("HTTP " + code);
            try (InputStream in = conn.getInputStream()) {
                return readBounded(in);
            }
        } finally {
            conn.disconnect();
        }
    }

    /**
     * Run a site script and take its stdout.
     *
     * A vendor CLI can hang, so the process gets a hard deadline and is killed on it. stdout is
     * drained on a helper thread rather than after {@code waitFor}: a script that fills the pipe
     * buffer while we wait would deadlock, and killing it is what unblocks the reader.
     */
    private String fetchScript(String cmd) throws IOException, InterruptedException {
        ProcessBuilder pb = new ProcessBuilder("/bin/sh", "-c", cmd);
        pb.redirectErrorStream(false);
        Process p = pb.start();
        StringBuilder out = new StringBuilder();
        StringBuilder err = new StringBuilder();
        IOException[] readError = new IOException[1];
        Thread reader = new Thread(() -> {
            try (InputStream in = p.getInputStream()) {
                out.append(readBounded(in));
            } catch (IOException e) {
                readError[0] = e;
            }
        });
        reader.setName("Scheduler-license-script");
        reader.setDaemon(true);
        reader.start();
        // Drain stderr too, or a chatty script blocks on a full stderr pipe
        // (~64KB) and never exits, turning a good answer into a fake timeout.
        // Kept bounded and only surfaced when the script fails.
        Thread errReader = new Thread(() -> {
            try (InputStream in = p.getErrorStream()) {
                err.append(readBounded(in));
            } catch (IOException e) {
                // Over the bound or broken pipe: stderr is diagnostics only.
            }
        });
        errReader.setName("Scheduler-license-script-err");
        errReader.setDaemon(true);
        errReader.start();
        boolean exited = p.waitFor(timeoutSeconds, TimeUnit.SECONDS);
        if (!exited) {
            p.destroyForcibly();
            reader.join(TimeUnit.SECONDS.toMillis(2));
            errReader.join(TimeUnit.SECONDS.toMillis(2));
            throw new IOException(
                    "script timed out after " + timeoutSeconds + "s" + errExcerpt(err));
        }
        reader.join(TimeUnit.SECONDS.toMillis(2));
        errReader.join(TimeUnit.SECONDS.toMillis(2));
        if (readError[0] != null)
            throw readError[0];
        if (p.exitValue() != 0)
            throw new IOException("script exited " + p.exitValue() + errExcerpt(err));
        return out.toString();
    }

    /** First 500 chars of the script's stderr, for failure messages only. */
    private static String errExcerpt(StringBuilder err) {
        if (err.length() == 0)
            return "";
        String s = err.substring(0, Math.min(err.length(), 500));
        return ", stderr: " + s.trim();
    }

    private static String readBounded(InputStream in) throws IOException {
        StringBuilder sb = new StringBuilder();
        char[] buf = new char[8192];
        try (BufferedReader r =
                new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            int n;
            while ((n = r.read(buf)) > 0) {
                sb.append(buf, 0, n);
                if (sb.length() > MAX_RESPONSE_BYTES)
                    throw new IOException(
                            "provider response over " + MAX_RESPONSE_BYTES + " bytes");
            }
        }
        return sb.toString();
    }

    // ---- helpers ---------------------------------------------------------

    /** {@code "hengine, katana"} to {@code [hengine, katana]}, lowercased, blanks dropped. */
    static List<String> splitNames(String csv) {
        List<String> out = new java.util.ArrayList<>(2);
        if (csv == null)
            return out;
        for (String part : csv.split(",")) {
            String s = part.trim().toLowerCase();
            if (!s.isEmpty() && !out.contains(s))
                out.add(s);
        }
        return out;
    }

    private static String str(JsonObject o, String key, String dflt) {
        JsonElement e = o.get(key);
        return (e == null || e.isJsonNull()) ? dflt : e.getAsString();
    }

    private static int num(JsonObject o, String key, int dflt) {
        JsonElement e = o.get(key);
        return (e == null || e.isJsonNull()) ? dflt : e.getAsInt();
    }

    private static long lng(JsonObject o, String key, long dflt) {
        JsonElement e = o.get(key);
        return (e == null || e.isJsonNull()) ? dflt : e.getAsLong();
    }

    private static boolean bool(JsonObject o, String key, boolean dflt) {
        JsonElement e = o.get(key);
        return (e == null || e.isJsonNull()) ? dflt : e.getAsBoolean();
    }
}
