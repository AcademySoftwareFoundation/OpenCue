"""PRODENV verdict: does the scheduler survive a chaotic production environment?

One process plays the admins and checks the books. Every CHAOS step (~2.5s) it
fires one weighted random mutation against the live farm, the kind operators do
all day: limit caps churn, folders appear with caps and eat running jobs, host
tags come and go, job max cores and subscription bursts random-walk under load,
hosts lock and unlock. Every second step it samples the invariants. Chaos stops
30s before the end (locks lifted, bursts restored) and the run closes with a
quiet reconciliation of every accounting mirror against the procs.

Cap invariants are DECAY-style, because a cap lowered below live usage legally
leaves procs running: after a grace window per mutation, usage that sits over
the current cap must not grow; growth is only legal under the cap. Mirrors get
gap+streak gates like capdrop_watch. Negative counters fail instantly.

  - PASS: every invariant held, coverage floors met, farm demonstrably flowed.
  - FAIL: a mirror wedged or went negative, an over-cap value kept growing, a
    locked host got new procs, a tag-stable host ran a mismatched layer, or the
    cuebot log shows a rejected flush.
  - INCONCLUSIVE: chaos coverage too thin to mean anything (not a pass).

usage: prodenv_watch.py [duration_s] [interval_s]
"""
import os, sys, time, random, subprocess, uuid
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 300
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 2.5
PSQL = spec.psql_cmd()
SEED = int(os.environ.get("SIM_PRODENV_SEED", "20260819"))
CUEBOT_LOG = os.environ.get("SIM_CUEBOT_LOG", "/tmp/cuebot-new.log")

GRACE = 8.0                 # seconds after a mutation before its invariant arms
JOB_SLACK_CP = int(os.environ.get("SIM_PRODENV_JOB_SLACK_CP", "8000"))
SUB_SLACK_CP = int(os.environ.get("SIM_PRODENV_SUB_SLACK_CP", "20000"))
DECAY_SLACK_CP = 400        # over-cap usage may jitter this much and not count
LIMIT_SLACK = 5             # frames of over-cap growth tolerated per sample
MIRROR_STREAK = 4           # consecutive bad mirror samples (~20s) = wedged
DECAY_STREAK = 3            # consecutive rising over-cap samples = violation
QUIESCE_S = 30              # chaos-free tail for reconciliation
MAX_LOCK_FRAC = 0.15
MAX_FOLDERS = 6
MIN_STARTED = 500           # frames started inside the window, else dead farm

FLUSH_SIGS = ("job/folder/point delta flush failed",
              "subscription delta flush failed",
              "layer_resource delta flush failed")


def q(sql, default=""):
    try:
        return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                              timeout=20).stdout.strip()
    except Exception:
        return default


def rows(sql):
    out = q(sql)
    return [ln.split("|") for ln in out.splitlines() if ln]


def scalar(sql, cast=int, default=0):
    try:
        return cast(q(sql))
    except Exception:
        return default


class Prodenv:

    def __init__(self):
        self.rng = random.Random(SEED)
        self.t0 = time.time()
        self.db_t0 = q("SELECT now();")
        self.actions = 0
        self.counts = {k: 0 for k in
                       ("limit", "folder", "tag", "jobcap", "burst", "lock")}
        self.fails = []
        # shows: name -> (pk_show, pk_alloc, root_folder, dept)
        self.shows = {}
        for pk_show, name, alloc in rows(
                "SELECT s.pk_show, s.str_name, sub.pk_alloc FROM show s "
                "JOIN subscription sub ON sub.pk_show = s.pk_show "
                "WHERE s.str_name LIKE 'show%';"):
            root, dept = rows(f"SELECT pk_folder, pk_dept FROM folder "
                              f"WHERE b_default = true AND pk_show = '{pk_show}';")[0]
            self.shows[name] = (pk_show, alloc, root, dept)
        self.hosts = rows("SELECT pk_host, str_name FROM host;")
        # live tag membership per pool, and the initial floor we never go under
        self.pool = {}
        for pk_host, tag in rows("SELECT pk_host, str_tag FROM host_tag WHERE "
                                 "str_tag ~ '^cap[0-9]+$' AND b_constant = false;"):
            self.pool.setdefault(tag, set()).add(pk_host)
        self.pool_floor = {tag: max(1, len(m) // 2) for tag, m in self.pool.items()}
        self.removed = {}       # (pk_host, tag) -> t removed
        self.tag_touch = {}     # pk_host -> t of last tag mutation
        self.locked = {}        # pk_host -> (t, db_ts, unlock_deadline)
        self.lock_hist = 0
        self.limits = {}
        self.limit_orig = {}
        self.limit_touch = {}
        self.limit_below = 0
        self.folders = []       # (pk_folder, show_name, cap_cp)
        self.folder_touch = {}
        self.folder_overcap = 0
        self.jobcaps = {}       # pk_job -> (orig_max, t touched)
        self.job_below = set()
        self.bursts = {}        # show -> (t touched, restore_deadline)
        self.burst_below = 0
        self.prev = {}          # decay state: key -> last usage
        self.streak = {}        # key -> consecutive bad samples
        self.worst = {}         # key family -> worst gap/streak for the verdict
        self.negatives = 0
        self.lock_viol = 0
        self.tag_viol = 0

    def now(self):
        return time.time() - self.t0

    def log(self, msg):
        print(f"t={self.now():5.0f} {msg}", flush=True)

    def fail(self, msg):
        if msg not in self.fails:
            self.fails.append(msg)
            self.log("INVARIANT FAIL: " + msg)

    # ---- chaos actors -------------------------------------------------------

    def reload_limits(self):
        """The injector creates the prodlim rows shortly after start; pick
        them up when they appear."""
        self.limits = {n: int(v) for n, v in
                       rows("SELECT str_name, int_max_value FROM limit_record "
                            "WHERE str_name LIKE 'prodlim%';")}
        self.limit_orig = dict(self.limits)
        self.limit_touch = {n: -1e9 for n in self.limits}

    def act_limit(self):
        if not self.limits:
            self.reload_limits()
            if not self.limits:
                return False
        name = self.rng.choice(list(self.limits))
        cap = (self.limit_orig[name] if self.rng.random() < 0.25
               else self.rng.randint(10, 400))
        q(f"UPDATE limit_record SET int_max_value = {cap} "
          f"WHERE str_name = '{name}';")
        running = scalar(
            f"SELECT count(*) FROM frame f "
            f"JOIN layer_limit ll ON ll.pk_layer = f.pk_layer "
            f"JOIN limit_record lr ON lr.pk_limit_record = ll.pk_limit_record "
            f"WHERE lr.str_name = '{name}' AND f.str_state = 'RUNNING';")
        if cap < running:
            self.limit_below += 1
        self.limits[name] = cap
        self.limit_touch[name] = self.now()
        self.counts["limit"] += 1
        self.log(f"CHAOS limit: {name} cap -> {cap} (running {running})")

    def act_folder(self):
        if len(self.folders) < MAX_FOLDERS and self.rng.random() < 0.6:
            show = self.rng.choice(list(self.shows))
            pk_show, _alloc, root, dept = self.shows[show]
            pk = str(uuid.uuid4())
            cap_cores = self.rng.randint(20, 300)
            q(f"INSERT INTO folder (pk_folder, pk_parent_folder, pk_show, "
              f"str_name, pk_dept) VALUES ('{pk}', '{root}', '{pk_show}', "
              f"'chaos{len(self.folders)}', '{dept}');"
              f"UPDATE folder_resource SET int_max_cores = {cap_cores * 100} "
              f"WHERE pk_folder = '{pk}';")
            moved = 0
            for (job_pk,) in [r[:1] for r in rows(
                    f"SELECT j.pk_job FROM job j "
                    f"JOIN job_resource jr ON jr.pk_job = j.pk_job "
                    f"WHERE j.pk_show = '{pk_show}' AND j.str_state = 'PENDING' "
                    f"AND jr.int_cores > 0 ORDER BY random() LIMIT "
                    f"{self.rng.randint(1, 3)};")]:
                q(f"UPDATE job SET pk_folder = '{pk}' WHERE pk_job = '{job_pk}';")
                moved += 1
            self.folders.append((pk, show, cap_cores * 100))
            self.folder_touch[pk] = self.now()
            self.log(f"CHAOS folder: created chaos folder on {show} "
                     f"cap={cap_cores} cores, moved {moved} live jobs in")
        elif self.folders:
            i = self.rng.randrange(len(self.folders))
            pk, show, _old = self.folders[i]
            cap_cores = (-1 if self.rng.random() < 0.2
                         else self.rng.randint(20, 300))
            q(f"UPDATE folder_resource SET int_max_cores = "
              f"{cap_cores * 100 if cap_cores > 0 else -1} "
              f"WHERE pk_folder = '{pk}';")
            self.folders[i] = (pk, show, cap_cores * 100 if cap_cores > 0 else -1)
            self.folder_touch[pk] = self.now()
            self.log(f"CHAOS folder: re-capped chaos folder on {show} "
                     f"-> {cap_cores} cores")
        else:
            return False
        self.counts["folder"] += 1
        return True

    def act_tag(self):
        tag = self.rng.choice(sorted(self.pool))
        members = self.pool[tag]
        removed_here = [k for k in self.removed if k[1] == tag]
        want_restore = (self.rng.random() < 0.4 and removed_here) or \
            len(members) <= self.pool_floor[tag] or \
            len(self.removed) >= len(self.hosts) // 10
        if want_restore and removed_here:
            pk_host, _ = removed_here[self.rng.randrange(len(removed_here))]
            q(f"INSERT INTO host_tag (pk_host_tag, pk_host, str_tag, "
              f"str_tag_type, b_constant) VALUES ('{uuid.uuid4()}', "
              f"'{pk_host}', '{tag}', 'Hardware', false);"
              f"SELECT recalculate_tags('{pk_host}');")
            del self.removed[(pk_host, tag)]
            members.add(pk_host)
            verb = "re-added"
        else:
            if len(members) <= self.pool_floor[tag]:
                return False
            pk_host = self.rng.choice(sorted(members))
            q(f"DELETE FROM host_tag WHERE pk_host = '{pk_host}' AND "
              f"str_tag = '{tag}' AND str_tag_type = 'Hardware' AND "
              f"b_constant = false;"
              f"SELECT recalculate_tags('{pk_host}');")
            self.removed[(pk_host, tag)] = self.now()
            members.discard(pk_host)
            verb = "removed"
        self.tag_touch[pk_host] = self.now()
        self.counts["tag"] += 1
        self.log(f"CHAOS tag: {verb} {tag} on one host "
                 f"(pool {len(members)}, farm removals {len(self.removed)})")
        return True

    def act_jobcap(self):
        if self.jobcaps and self.rng.random() < 0.33:
            pk = self.rng.choice(sorted(self.jobcaps))
            orig, _ = self.jobcaps[pk]
            q(f"UPDATE job_resource SET int_max_cores = {orig} "
              f"WHERE pk_job = '{pk}';")
            self.jobcaps[pk] = (orig, self.now())
            self.job_below.discard(pk)
            self.log("CHAOS jobcap: restored one job's max cores")
        else:
            r = rows("SELECT jr.pk_job, jr.int_cores, jr.int_max_cores "
                     "FROM job_resource jr JOIN job j ON j.pk_job = jr.pk_job "
                     "WHERE j.str_state = 'PENDING' AND jr.int_cores >= 1000 "
                     "ORDER BY random() LIMIT 1;")
            if not r:
                return False
            pk, usage, cur_max = r[0][0], int(r[0][1]), int(r[0][2])
            new_max = max(100, int(usage * self.rng.uniform(0.3, 1.5)))
            if new_max < usage and len(self.job_below) >= 10:
                new_max = usage + 100
            q(f"UPDATE job_resource SET int_max_cores = {new_max} "
              f"WHERE pk_job = '{pk}';")
            if pk not in self.jobcaps:
                self.jobcaps[pk] = (cur_max, self.now())
            else:
                self.jobcaps[pk] = (self.jobcaps[pk][0], self.now())
            if new_max < usage:
                self.job_below.add(pk)
            self.log(f"CHAOS jobcap: job max -> {new_max}cp "
                     f"(usage {usage}cp, below={new_max < usage})")
        self.counts["jobcap"] += 1
        return True

    def act_burst(self):
        show = self.rng.choice(sorted(self.shows))
        pk_show, alloc, _root, _dept = self.shows[show]
        truth = scalar(
            f"SELECT COALESCE(SUM(p.int_cores_reserved), 0) FROM proc p "
            f"JOIN host h ON h.pk_host = p.pk_host "
            f"WHERE p.pk_show = '{pk_show}' AND h.pk_alloc = '{alloc}';")
        factor = self.rng.uniform(0.5, 1.2)
        burst = max(1, int(truth * factor))
        if truth > 0:
            burst = max(burst, truth // 5)
        if factor < 1.0 and len(self.bursts) >= 2 and show not in self.bursts:
            factor, burst = 1.2, max(1, int(truth * 1.2))
        q(f"UPDATE subscription SET int_burst = {burst} "
          f"WHERE pk_show = '{pk_show}' AND pk_alloc = '{alloc}';")
        if burst < truth:
            self.burst_below += 1
        self.bursts[show] = (self.now(), self.now() + self.rng.uniform(30, 60))
        self.counts["burst"] += 1
        self.log(f"CHAOS burst: {show} burst -> {burst}cp (usage {truth}cp)")
        return True

    def act_lock(self):
        if (len(self.locked) < int(len(self.hosts) * MAX_LOCK_FRAC)
                and self.rng.random() < 0.7):
            pk_host, name = self.rng.choice(self.hosts)
            if pk_host in self.locked:
                return False
            db_ts = q(f"UPDATE host SET str_lock_state = 'LOCKED' "
                      f"WHERE pk_host = '{pk_host}' RETURNING now();")
            self.locked[pk_host] = (self.now(), db_ts,
                                    self.now() + self.rng.uniform(20, 45))
            self.lock_hist += 1
            self.log(f"CHAOS lock: LOCKED {name} ({len(self.locked)} locked)")
        elif self.locked:
            pk_host = self.rng.choice(sorted(self.locked))
            self.unlock(pk_host)
        else:
            return False
        self.counts["lock"] += 1
        return True

    def unlock(self, pk_host):
        q(f"UPDATE host SET str_lock_state = 'OPEN' WHERE pk_host = '{pk_host}';")
        self.locked.pop(pk_host, None)
        self.log(f"CHAOS lock: unlocked one host ({len(self.locked)} locked)")

    def housekeeping(self):
        t = self.now()
        for pk_host in [h for h, (_, _, dl) in self.locked.items() if t > dl]:
            self.unlock(pk_host)
        for show in [s for s, (_, dl) in self.bursts.items() if t > dl]:
            pk_show, alloc, _r, _d = self.shows[show]
            q(f"UPDATE subscription SET int_burst = 1000000000 "
              f"WHERE pk_show = '{pk_show}' AND pk_alloc = '{alloc}';")
            del self.bursts[show]
            self.log(f"CHAOS burst: {show} burst restored")

    def chaos_step(self):
        self.housekeeping()
        acts = [(self.act_limit, 0.20), (self.act_folder, 0.15),
                (self.act_tag, 0.20), (self.act_jobcap, 0.15),
                (self.act_burst, 0.15), (self.act_lock, 0.15)]
        # Two independent draws per step: a real ops day never queues politely.
        for _ in range(2):
            x = self.rng.random()
            for fn, w in acts:
                if x < w:
                    if fn() is not False:
                        self.actions += 1
                    break
                x -= w
            else:
                if self.act_limit() is not False:
                    self.actions += 1

    # ---- invariants ---------------------------------------------------------

    def decay(self, key, usage, cap, touch_t, slack):
        """Over-cap usage must not grow once the mutation grace has passed."""
        prev = self.prev.get(key)
        self.prev[key] = usage
        if cap < 0 or usage <= cap or self.now() - touch_t < GRACE or prev is None:
            self.streak[key] = 0
            return
        bad = usage > prev + slack
        self.streak[key] = self.streak[key] + 1 if bad else 0
        fam = key.split(":")[0]
        self.worst[fam] = max(self.worst.get(fam, 0), self.streak[key])
        if self.streak[key] >= DECAY_STREAK:
            self.fail(f"{key} kept growing over its cap "
                      f"({usage} > cap {cap}, streak {self.streak[key]})")

    def mirror(self, key, gap, slack):
        bad = gap > slack
        self.streak[key] = self.streak.get(key, 0) + 1 if bad else 0
        fam = key.split(":")[0]
        g, s = self.worst.get(fam, (0, 0))
        self.worst[fam] = (max(g, gap), max(s, self.streak[key]))
        if self.streak[key] >= MIRROR_STREAK:
            self.fail(f"{key} mirror diverged (gap {gap}cp, "
                      f"streak {self.streak[key]})")

    def sample(self):
        r = rows("SELECT COALESCE(MAX(ABS(jr.int_cores - COALESCE(p.c, 0))), 0), "
                 "COALESCE(MIN(jr.int_cores), 0) FROM job_resource jr "
                 "JOIN job j ON j.pk_job = jr.pk_job "
                 "LEFT JOIN (SELECT pk_job, SUM(int_cores_reserved) c FROM proc "
                 "GROUP BY pk_job) p ON p.pk_job = jr.pk_job "
                 "WHERE j.str_state = 'PENDING';")
        if r:
            gap, mn = int(r[0][0]), int(r[0][1])
            self.mirror("job", gap, JOB_SLACK_CP)
            if mn < 0:
                self.fail(f"job_resource.int_cores went NEGATIVE ({mn}cp)")
        for name, mir, truth in rows(
                "SELECT s.str_name, sub.int_cores, COALESCE(t.c, 0) "
                "FROM subscription sub JOIN show s ON s.pk_show = sub.pk_show "
                "LEFT JOIN (SELECT p.pk_show, h.pk_alloc, "
                "SUM(p.int_cores_reserved) c FROM proc p "
                "JOIN host h ON h.pk_host = p.pk_host GROUP BY 1, 2) t "
                "ON t.pk_show = sub.pk_show AND t.pk_alloc = sub.pk_alloc "
                "WHERE s.str_name LIKE 'show%';"):
            mir, truth = int(mir), int(truth)
            self.mirror(f"sub:{name}", abs(mir - truth), SUB_SLACK_CP)
            if mir < 0:
                self.fail(f"subscription {name} mirror went NEGATIVE ({mir}cp)")
            if name in self.bursts:
                pk_show, alloc, _r, _d = self.shows[name]
                burst = scalar(f"SELECT int_burst FROM subscription WHERE "
                               f"pk_show = '{pk_show}' AND pk_alloc = '{alloc}';")
                self.decay(f"burst:{name}", truth, burst,
                           self.bursts[name][0], DECAY_SLACK_CP)
        for name in self.limits:
            cap = scalar(f"SELECT int_max_value FROM limit_record "
                         f"WHERE str_name = '{name}';", int, -1)
            run = scalar(
                f"SELECT count(*) FROM frame f "
                f"JOIN layer_limit ll ON ll.pk_layer = f.pk_layer "
                f"JOIN limit_record lr ON lr.pk_limit_record = ll.pk_limit_record "
                f"WHERE lr.str_name = '{name}' AND f.str_state = 'RUNNING';")
            self.decay(f"limit:{name}", run, cap, self.limit_touch[name],
                       LIMIT_SLACK)
        for pk, show, cap_cp in self.folders:
            usage = scalar(f"SELECT COALESCE(SUM(p.int_cores_reserved), 0) "
                           f"FROM proc p JOIN job j ON j.pk_job = p.pk_job "
                           f"WHERE j.pk_folder = '{pk}';")
            if cap_cp >= 0 and usage > cap_cp:
                self.folder_overcap += 1
            self.decay(f"folder:{pk[:8]}", usage, cap_cp,
                       self.folder_touch[pk], DECAY_SLACK_CP)
        for pk in sorted(self.job_below):
            r2 = rows(f"SELECT COALESCE(SUM(int_cores_reserved), 0), "
                      f"(SELECT int_max_cores FROM job_resource "
                      f"WHERE pk_job = '{pk}') FROM proc WHERE pk_job = '{pk}';")
            if r2 and r2[0][1]:
                self.decay(f"jobcap:{pk[:8]}", int(r2[0][0]), int(r2[0][1]),
                           self.jobcaps[pk][1], DECAY_SLACK_CP)
        ripe = [(h, ts) for h, (t, ts, _dl) in self.locked.items()
                if self.now() - t >= GRACE and ts]
        if ripe:
            vals = ",".join(f"('{h}', '{ts}')" for h, ts in ripe)
            v = scalar(f"SELECT count(*) FROM proc p JOIN (VALUES {vals}) "
                       f"v(pk, ts) ON p.pk_host = v.pk "
                       f"AND p.ts_booked > v.ts::timestamptz "
                       f"+ interval '{int(GRACE)} seconds';")
            if v > 0:
                self.lock_viol += v
                self.fail(f"{v} proc(s) booked on LOCKED hosts")
        recent = [h for h, t in self.tag_touch.items()
                  if self.now() - t < GRACE + 6]
        skip = ("AND p.pk_host NOT IN (" +
                ",".join(f"'{h}'" for h in recent) + ") ") if recent else ""
        v = scalar(f"SELECT count(*) FROM proc p "
                   f"JOIN host h ON h.pk_host = p.pk_host "
                   f"JOIN layer l ON l.pk_layer = p.pk_layer "
                   f"WHERE p.ts_booked > now() - interval '6 seconds' {skip}"
                   f"AND l.str_tags <> '' AND l.str_tags !~ ' ' "
                   f"AND NOT (h.str_tags ~ ('(^| )' || l.str_tags || '( |$)'));")
        if v > 0:
            self.tag_viol += v
            self.fail(f"{v} proc(s) booked on hosts missing the layer's tag")
        neg = scalar(
            "SELECT (SELECT count(*) FROM job_resource WHERE int_cores < 0) + "
            "(SELECT count(*) FROM subscription WHERE int_cores < 0) + "
            "(SELECT count(*) FROM folder_resource WHERE int_cores < 0) + "
            "(SELECT count(*) FROM layer_resource WHERE int_cores < 0) + "
            "(SELECT count(*) FROM host WHERE int_cores_idle < 0 "
            "OR int_mem_idle < 0);")
        if neg > 0:
            self.negatives += neg
            self.fail(f"{neg} negative resource counter(s) in the DB")
        jg, js = self.worst.get("job", (0, 0))
        self.log(f"sample: job gap {jg}cp streak {js} | locked "
                 f"{len(self.locked)} | folders {len(self.folders)} | "
                 f"actions {self.actions}")

    # ---- endgame ------------------------------------------------------------

    def quiesce(self):
        self.log("quiesce: chaos stops, unlocking hosts, restoring bursts")
        for pk_host in list(self.locked):
            self.unlock(pk_host)
        for show in list(self.bursts):
            pk_show, alloc, _r, _d = self.shows[show]
            q(f"UPDATE subscription SET int_burst = 1000000000 "
              f"WHERE pk_show = '{pk_show}' AND pk_alloc = '{alloc}';")
            del self.bursts[show]

    def reconcile_once(self):
        jr = scalar("SELECT COALESCE(SUM(jr.int_cores), 0) FROM job_resource jr "
                    "JOIN job j ON j.pk_job = jr.pk_job "
                    "WHERE j.str_state = 'PENDING';")
        pr = scalar("SELECT COALESCE(SUM(int_cores_reserved), 0) FROM proc;")
        sub_gap = 0
        for _n, mir, truth in rows(
                "SELECT s.str_name, sub.int_cores, COALESCE(t.c, 0) "
                "FROM subscription sub JOIN show s ON s.pk_show = sub.pk_show "
                "LEFT JOIN (SELECT p.pk_show, h.pk_alloc, "
                "SUM(p.int_cores_reserved) c FROM proc p "
                "JOIN host h ON h.pk_host = p.pk_host GROUP BY 1, 2) t "
                "ON t.pk_show = sub.pk_show AND t.pk_alloc = sub.pk_alloc "
                "WHERE s.str_name LIKE 'show%';"):
            sub_gap = max(sub_gap, abs(int(mir) - int(truth)))
        fr = scalar("SELECT COALESCE(SUM(int_cores), 0) FROM folder_resource;")
        return abs(jr - pr), sub_gap, abs(fr - jr)

    def verdict(self):
        started = scalar(f"SELECT count(*) FROM frame "
                         f"WHERE ts_started > '{self.db_t0}'::timestamptz;")
        flush = tick = 0
        try:
            cb = open(CUEBOT_LOG, errors="ignore").read()
            flush = sum(cb.count(s) for s in FLUSH_SIGS)
            tick = cb.count("Scheduler tick failed")
        except Exception:
            pass
        if flush > 0:
            self.fail(f"{flush} rejected delta flush(es) in the cuebot log")
        if tick > 2:
            self.fail(f"{tick} scheduler tick failures (tolerance 2)")
        if started < MIN_STARTED:
            self.fail(f"only {started} frames started in the window "
                      f"(floor {MIN_STARTED}): the farm was not working")
        floors_ok = (self.actions >= 120
                     and all(c >= 8 for c in self.counts.values())
                     and self.limit_below >= 1 and self.folder_overcap >= 1
                     and self.counts["tag"] >= 20 and self.lock_hist >= 8
                     and self.burst_below >= 2)
        jg, js = self.worst.get("job", (0, 0))
        sg, ss = max((v for k, v in self.worst.items()
                      if k.startswith("sub")), default=(0, 0))
        print("\n==== PRODENV VERDICT ====", flush=True)
        print(f"chaos actions={self.actions} seed={SEED} "
              + " ".join(f"{k}={v}" for k, v in sorted(self.counts.items())),
              flush=True)
        print(f"job worst gap {jg}cp streak {js}; sub worst gap {sg}cp "
              f"streak {ss}; negatives={self.negatives} "
              f"lock violations={self.lock_viol} tag violations={self.tag_viol}",
              flush=True)
        print(f"flush rejections={flush} tick fails={tick} "
              f"frames started={started}", flush=True)
        if self.fails:
            print("FAIL: " + "; ".join(self.fails[:4]), flush=True)
        elif not floors_ok:
            print(f"INCONCLUSIVE: chaos coverage too thin "
                  f"(actions={self.actions}, per-actor={self.counts}, "
                  f"limit_below={self.limit_below}, "
                  f"folder_overcap={self.folder_overcap}, "
                  f"burst_below={self.burst_below}, locks={self.lock_hist}); "
                  f"nothing proven.", flush=True)
        else:
            print(f"PASS: every mirror tracked the procs and every cap decayed "
                  f"cleanly through {self.actions} chaotic admin mutations on "
                  f"a live farm, with zero rejected flushes.", flush=True)

    def run(self):
        print(f"watching PRODENV for {DURATION}s: chaotic admin mutations "
              f"(seed {SEED}) every {INTERVAL}s under full load; invariants "
              f"every {2 * INTERVAL}s; quiesce at t={DURATION - QUIESCE_S}s.\n",
              flush=True)
        # let the farm come alive and the injector seed its limits before the
        # first mutation, so early chaos hits real load
        while self.now() < min(45, DURATION / 4):
            if not self.limits:
                self.reload_limits()
            if self.limits and scalar("SELECT count(*) FROM proc;") > 2000:
                break
            time.sleep(INTERVAL)
        step = 0
        quiesced = False
        while self.now() < DURATION:
            if not quiesced and self.now() >= DURATION - QUIESCE_S:
                self.quiesce()
                quiesced = True
            if not quiesced:
                self.chaos_step()
            step += 1
            if step % 2 == 0:
                self.sample()
            time.sleep(INTERVAL)
        g1 = self.reconcile_once()
        time.sleep(10)
        g2 = self.reconcile_once()
        best = min(g1, g2)
        self.log(f"reconciliation: job-sum gap {best[0]}cp, worst sub gap "
                 f"{best[1]}cp, folder-sum gap {best[2]}cp")
        if best[0] > JOB_SLACK_CP:
            self.fail(f"final job_resource sum off by {best[0]}cp")
        if best[1] > SUB_SLACK_CP:
            self.fail(f"final subscription mirror off by {best[1]}cp")
        if best[2] > JOB_SLACK_CP:
            self.fail(f"final folder_resource sum off by {best[2]}cp")
        self.verdict()


if __name__ == "__main__":
    Prodenv().run()
