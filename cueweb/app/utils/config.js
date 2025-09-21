// Note: each key/value is initialized as 'name': process.env.name because accessing environment variables at runtime using a for loop
// sometimes causes the environment variable to be undefined even if it exists and is accessible on the client side
// ex: 
// for (const varName in clientEnvVars) {
//     console.log(process.env.NEXT_PUBLIC_URL); // This properly prints out NEXT_PUBLIC_URL's value
//     console.log(process.env["NEXT_PUBLIC_URL"]); // This properly prints out NEXT_PUBLIC_URL's value
//     console.log(process.env[varName]); // This prints out undefined
// }

// Loads and verifies server side environment variables (non NEXT_PUBLIC_... variables)
function loadServerEnvVars() {
    // The server and client have different dictionaries because they have different access to environment variables
    // - Server: all environment variables
    // - client: public environment variables (variables that start with NEXT_PUBLIC)
    let serverEnvVars = {
        "NEXT_PUBLIC_OPENCUE_ENDPOINT": process.env.NEXT_PUBLIC_OPENCUE_ENDPOINT,
        "NEXT_PUBLIC_URL": process.env.NEXT_PUBLIC_URL,
        "NEXT_JWT_SECRET": process.env.NEXT_JWT_SECRET,
    };

    const optionalNextAuthVars = {
        "NEXT_PUBLIC_AUTH_PROVIDER": process.env.NEXT_PUBLIC_AUTH_PROVIDER,
        "NEXTAUTH_URL": process.env.NEXTAUTH_URL,
        "NEXTAUTH_SECRET": process.env.NEXTAUTH_SECRET,
        "NEXT_AUTH_OKTA_CLIENT_ID": process.env.NEXT_AUTH_OKTA_CLIENT_ID,
        "NEXT_AUTH_OKTA_ISSUER": process.env.NEXT_AUTH_OKTA_ISSUER,
        "NEXT_AUTH_OKTA_CLIENT_SECRET": process.env.NEXT_AUTH_OKTA_CLIENT_SECRET,
    }

    const optionalSentryVars = {
        "SENTRY_ENVIRONMENT": process.env.SENTRY_ENVIRONMENT,
        "SENTRY_PROJECT": process.env.SENTRY_PROJECT,
        "SENTRY_ORG": process.env.SENTRY_ORG,
        "SENTRY_URL": process.env.SENTRY_URL,
        "SENTRY_DSN": process.env.SENTRY_DSN,
    }

    if (process.env.NEXT_PUBLIC_AUTH_PROVIDER) {
        serverEnvVars = { ...serverEnvVars, ...optionalNextAuthVars };
    }

    if (process.env.SENTRY_DSN) {
        serverEnvVars = { ...serverEnvVars, ...optionalSentryVars };
    }

    // Iterate through the environment variables and verify them
    for (const varName in serverEnvVars) {
        if (serverEnvVars[varName] === undefined) {
            // Throw an error and stop the program if an environment variable is not defined
            // We can't throw a Sentry error since this is ran before Sentry is initialized
            // (Sentry initialization depends on environment variables)
            const error = `Missing or unaccessible environment variable \'${varName}\'`;
            console.error(error);
            throw new Error(error);
        }
    }
}

// Loads and verifies client side environment variables (NEXT_PUBLIC_ ...)
function loadClientEnvVars() {
    // The server and client have different dictionaries because they have different access to environment variables
    // - Server: all environment variables
    // - client: public environment variables (variables that start with NEXT_PUBLIC)
    const clientEnvVars = {
        "NEXT_PUBLIC_OPENCUE_ENDPOINT": process.env.NEXT_PUBLIC_OPENCUE_ENDPOINT,
        "NEXT_PUBLIC_URL": process.env.NEXT_PUBLIC_URL,
        ...(process.env.NEXT_PUBLIC_AUTH_PROVIDER ? { "NEXT_PUBLIC_AUTH_PROVIDER": process.env.NEXT_PUBLIC_AUTH_PROVIDER } : { }),
    }

    for (const varName in clientEnvVars) {
        if (clientEnvVars[varName] === undefined) {
            const error = `Missing or unaccessible environment variable \'${varName}\'`;
            console.error(error);
            throw new Error(error);
        }
    }
}

module.exports = {
    loadServerEnvVars,
    loadClientEnvVars,
};
