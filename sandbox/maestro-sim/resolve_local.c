/*
 * getaddrinfo LD_PRELOAD shim for `simulate.py --mode rust --rust-real-launch`.
 *
 * The Rust scheduler (cue-scheduler) is a native binary, so the JVM hosts file
 * (-Djdk.net.hosts.file) cuebot uses to point farm hostnames at fake_rqd does
 * not apply to it. This shim is the native analog: it intercepts glibc
 * getaddrinfo and sends every *named* lookup to loopback, so the scheduler's
 * per-host RQD dials (http://<host.name>:8444) reach fake_rqd on 127.0.0.1. In
 * the sim every target -- Postgres, Redis, each farm host's RQD -- is local, so
 * a blanket redirect is correct. A NULL node (passive/bind, e.g. the metrics
 * port) is left untouched so listening sockets still bind normally.
 *
 * Built (once) into resolve_local.so by ensure_resolver_shim() in simulate.py
 * and LD_PRELOADed onto the scheduler process only:
 *   gcc -shared -fPIC -o resolve_local.so resolve_local.c -ldl
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <netdb.h>

static int (*real_getaddrinfo)(const char *, const char *,
                               const struct addrinfo *, struct addrinfo **) = 0;

int getaddrinfo(const char *node, const char *service,
                const struct addrinfo *hints, struct addrinfo **res) {
    if (!real_getaddrinfo)
        real_getaddrinfo = dlsym(RTLD_NEXT, "getaddrinfo");
    if (node)
        node = "127.0.0.1";
    return real_getaddrinfo(node, service, hints, res);
}
