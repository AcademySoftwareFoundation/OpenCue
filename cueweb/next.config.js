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

// Read the package.json version once at build time so we can expose it to
// the client as `process.env.NEXT_PUBLIC_APP_VERSION`. An explicit
// NEXT_PUBLIC_APP_VERSION env var (e.g. set in the Dockerfile to a Git SHA
// or CI build number) takes precedence over the package.json value.
const PKG_VERSION = (() => {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    return require("./package.json").version || "";
  } catch (_) {
    return "";
  }
})();
process.env.NEXT_PUBLIC_APP_VERSION =
  process.env.NEXT_PUBLIC_APP_VERSION || PKG_VERSION;

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
  // Whitelist NEXT_PUBLIC_APP_VERSION so it's inlined into the client bundle.
  env: {
    NEXT_PUBLIC_APP_VERSION: process.env.NEXT_PUBLIC_APP_VERSION,
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
