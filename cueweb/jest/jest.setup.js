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

// Set up environment variables before each test
beforeEach(() => {
    // Define environment variables with placeholder values for testing
    const envVars = {
        NEXT_PUBLIC_OPENCUE_ENDPOINT: 'NEXT_PUBLIC_OPENCUE_ENDPOINT',
        NEXT_PUBLIC_AUTH_PROVIDER: 'NEXT_PUBLIC_AUTH_PROVIDER',
        NEXT_PUBLIC_URL: 'NEXT_PUBLIC_URL',
        NEXTAUTH_URL: 'NEXTAUTH_URL',
        NEXTAUTH_SECRET: 'NEXTAUTH_SECRET',
        NEXT_JWT_SECRET: 'NEXT_JWT_SECRET',
        NEXT_AUTH_OKTA_CLIENT_ID: 'NEXT_AUTH_OKTA_CLIENT_ID',
        NEXT_AUTH_OKTA_ISSUER: 'NEXT_AUTH_OKTA_ISSUER',
        NEXT_AUTH_OKTA_CLIENT_SECRET: 'NEXT_AUTH_OKTA_CLIENT_SECRET',
        SENTRY_ENVIRONMENT: 'SENTRY_ENVIRONMENT',
        SENTRY_PROJECT: 'SENTRY_PROJECT',
        SENTRY_URL: 'SENTRY_URL',
        SENTRY_ORG: 'SENTRY_ORG',
        SENTRY_DSN: 'SENTRY_DSN',
    };

    // Validate that all required environment variables are set
    for (const [key, value] of Object.entries(envVars)) {
        if (!value) {
            throw new Error(`Environment variable ${key} is not set.`);
        }
    }

    // Assign environment variables to process.env
    process.env = envVars;
});
