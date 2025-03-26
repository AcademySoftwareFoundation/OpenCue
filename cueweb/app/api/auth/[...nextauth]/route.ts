/**
 * The `authOptions` import from "@/lib/auth" contains configuration settings for NextAuth,
 * a library used for authentication in Next.js applications. These settings dictate how
 * authentication is handled within the application, including specifying the authentication providers,
 * callbacks, database options, and other custom configurations necessary for managing user sessions.
 *
 * NextAuth is configured here to streamline the authentication process, offering a simple and secure method
 * for handling user logins, registrations, and session management. By using `authOptions`, we can customize
 * the behavior of NextAuth to fit the specific needs of our application, such as integrating with different
 * OAuth providers (e.g., Google Gmail, Microsoft Outlook, GitHub, Okta) and managing session tokens.
 *
 * For more detailed information on NextAuth and its configuration options, refer to the official documentation:
 * https://next-auth.js.org/
 */
import {authOptions} from "@/lib/auth";
import NextAuth from "next-auth/next";

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };