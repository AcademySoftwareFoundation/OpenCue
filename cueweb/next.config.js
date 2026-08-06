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

/** @type {import('next').NextConfig} */
const { loadServerEnvVars } = require("./app/utils/config");
// Verify that all environment variables exist and throws an error if they are not defined
loadServerEnvVars();

// Resolve the CueWeb version once at build time and expose it to the client as
// `process.env.NEXT_PUBLIC_APP_VERSION`. Resolution order (first hit wins):
//   1. NEXT_PUBLIC_APP_VERSION env / build-arg (CI injects the generated
//      OpenCue version or a Git SHA) - always takes precedence.
//   2. cueweb/OVERRIDE_CUEWEB_VERSION.in:
//        - value "VERSION.in" (the default) -> use the repo-root VERSION.in
//          (OpenCue's shared source of truth, also read by cuebot / cuegui).
//        - any other value -> use it verbatim (an explicit per-CueWeb override).
//   3. package.json `version` (last-resort fallback).
const fs = require("fs");
const path = require("path");
// First non-comment, non-blank line of a file (trimmed); "" if unreadable.
function firstValueLine(relPath) {
  try {
    const raw = fs.readFileSync(path.join(__dirname, relPath), "utf8");
    return (
      raw
        .split(/\r?\n/)
        .map((l) => l.trim())
        .find((l) => l.length > 0 && !l.startsWith("#")) || ""
    );
  } catch (_) {
    return "";
  }
}
const RESOLVED_VERSION = (() => {
  const override = firstValueLine("./OVERRIDE_CUEWEB_VERSION.in");
  // An explicit override (anything other than the "VERSION.in" sentinel) wins.
  if (override && override !== "VERSION.in") return override;
  // Sentinel (or missing override file): track the repo-root VERSION.in. In the
  // Docker image it is copied to ../VERSION.in via the build's project_root
  // additional context (see Dockerfile / docker-compose.yml).
  const rootVersion = firstValueLine("../VERSION.in");
  if (rootVersion) return rootVersion;
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    return require("./package.json").version || "";
  } catch (_) {
    return "";
  }
})();
process.env.NEXT_PUBLIC_APP_VERSION =
  process.env.NEXT_PUBLIC_APP_VERSION || RESOLVED_VERSION;

// Build SHA shown in the About CueWeb dialog. Defaults to empty (the dialog
// renders "unknown") when CI doesn't inject it.
process.env.NEXT_PUBLIC_GIT_SHA = process.env.NEXT_PUBLIC_GIT_SHA || "";

const nextConfig = {
  // WebPack is a module bundler for JavaScript applications
  // Running NextJS in dev mode allows webpack to watch for file changes and rebuild when changes happen
  webpack: config => {
    config.watchOptions = {
      // The interval in milliseconds that webpack checks for file changes
      poll: 1000,

      // The delay in milliseconds before webpack rebuilds the app (after first file change)
      aggregateTimeout: 300,
    }
    return config
  },
  // Whitelist build-time vars so they're inlined into the client bundle.
  env: {
    NEXT_PUBLIC_APP_VERSION: process.env.NEXT_PUBLIC_APP_VERSION,
    NEXT_PUBLIC_GIT_SHA: process.env.NEXT_PUBLIC_GIT_SHA,
  },
};

module.exports = nextConfig;


// Injected content via Sentry wizard below

const { withSentryConfig } = require("@sentry/nextjs");

module.exports = withSentryConfig(
  module.exports,
  {
    // For all available options, see:
    // https://github.com/getsentry/sentry-webpack-plugin#options

    // Suppresses source map uploading logs during build
    silent: true,
    org: process.env.SENTRY_ORG,
    project: process.env.SENTRY_PROJECT,
    url: process.env.SENTRY_URL
  },
  {
    // For all available options, see:
    // https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/

    // Upload a larger set of source maps for prettier stack traces (increases build time)
    widenClientFileUpload: true,

    // Transpiles SDK to be compatible with IE11 (increases bundle size)
    transpileClientSDK: true,

    // Routes browser requests to Sentry through a Next.js rewrite to circumvent ad-blockers. (increases server load)
    // Note: Check that the configured route will not match with your Next.js middleware, otherwise reporting of client-
    // side errors will fail.
    tunnelRoute: "/monitoring",

    // Hides source maps from generated client bundles
    hideSourceMaps: true,

    // Automatically tree-shake Sentry logger statements to reduce bundle size
    disableLogger: true,

    // Enables automatic instrumentation of Vercel Cron Monitors.
    // See the following for more information:
    // https://docs.sentry.io/product/crons/
    // https://vercel.com/docs/cron-jobs
    automaticVercelMonitors: true,
  }
);
