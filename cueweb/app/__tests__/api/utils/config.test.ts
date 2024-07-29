import { loadClientEnvVars, loadServerEnvVars } from '@/app/utils/config';

describe('loadServerEnvVars', () => {

    // All environment variables are already defined before the test.
    // Their values are then loaded and checked against their expected values.
    it('should load and verify environment variables', () => {
        const envVars = loadServerEnvVars();

        expect(envVars.NEXTAUTH_URL).toBe('NEXTAUTH_URL')
        expect(envVars.NEXTAUTH_SECRET).toBe('NEXTAUTH_SECRET')
        expect(envVars.NEXT_JWT_SECRET).toBe('NEXT_JWT_SECRET')
        expect(envVars.NEXT_AUTH_OKTA_CLIENT_ID).toBe('NEXT_AUTH_OKTA_CLIENT_ID')
        expect(envVars.NEXT_AUTH_OKTA_ISSUER).toBe('NEXT_AUTH_OKTA_ISSUER')
        expect(envVars.NEXT_AUTH_OKTA_CLIENT_SECRET).toBe('NEXT_AUTH_OKTA_CLIENT_SECRET')
        expect(envVars.SENTRY_ENVIRONMENT).toBe('SENTRY_ENVIRONMENT')
        expect(envVars.SENTRY_PROJECT).toBe('SENTRY_PROJECT')
        expect(envVars.SENTRY_URL).toBe('SENTRY_URL')
        expect(envVars.SENTRY_ORG).toBe('SENTRY_ORG')
        expect(envVars.SENTRY_DSN).toBe('SENTRY_DSN')
    });

    it('should log an error if a required env var is missing', () => {
        // Spy on console.error to check for error messages
        const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
        // Delete an environment variable so we can later check for errors
        delete process.env.NEXT_JWT_SECRET;

        // Since we deleted an environmnet variable, we expect an error to be thrown for the mising variable and a console.error
        try {
            loadServerEnvVars();
        } catch (error) {
            expect((error as Error).message).toBe("Missing or unaccessible environment variable 'NEXT_JWT_SECRET'");
        }
        expect(consoleErrorSpy).toHaveBeenCalledWith("Missing or unaccessible environment variable 'NEXT_JWT_SECRET'");
        
        consoleErrorSpy.mockRestore();
    });
});

describe('loadClientEnvVars', () => {

    // All environment variables are already defined before the test.
    // Their values are then loaded and checked against their expected values.
    it('should load and verify environment variables', () => {
        const envVars = loadClientEnvVars();

        expect(envVars.NEXT_PUBLIC_OPENCUE_ENDPOINT).toBe('NEXT_PUBLIC_OPENCUE_ENDPOINT')
        expect(envVars.NEXT_PUBLIC_URL).toBe('NEXT_PUBLIC_URL')
        expect(envVars.NEXT_PUBLIC_AUTH_PROVIDER).toBe('NEXT_PUBLIC_AUTH_PROVIDER')
    });

    it('should log an error if a required env var is missing', () => {
        // Spy on console.error to check for error messages
        const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
        // Delete an environment variable so we can later check for errors
        delete process.env.NEXT_PUBLIC_URL;

        // Since we deleted an environmnet variable, we expect an error to be thrown for the mising variable and a console.error
        try {
            loadClientEnvVars();
        } catch (error) {
            expect((error as Error).message).toBe("Missing or unaccessible environment variable 'NEXT_PUBLIC_URL'");
        }
        expect(consoleErrorSpy).toHaveBeenCalledWith("Missing or unaccessible environment variable 'NEXT_PUBLIC_URL'");
        
        consoleErrorSpy.mockRestore();
    });
});

export { };
