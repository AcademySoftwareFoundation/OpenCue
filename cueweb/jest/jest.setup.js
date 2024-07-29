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
