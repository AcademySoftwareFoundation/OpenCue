FROM node:21-alpine

WORKDIR /opt/cueweb

# If needed, you can change the registry where packages are fetched from
# RUN npm config set registry <your artifactory url>

# install dependencies before copying the source code
COPY package*.json ./

# when SENTRYCLI_USE_LOCAL is set to 1, sentry-cli binary will be discovered from $PATH and copied locally, instead
# of being downloaded from external servers. (https://docs.sentry.io/product/cli/installation/)
# This is necessary if the firewall blocks downloads from external servers
# sentry-cli is needed to upload source maps to sentry
# ENV SENTRYCLI_USE_LOCAL=1

# Skip downloading the sentry-cli binary entirely
ENV SENTRYCLI_SKIP_DOWNLOAD=1
# run npm install if npm ci is not working properly because of the package-lock.json
# RUN npm install
RUN npm ci

COPY *.json /opt/cueweb/
COPY next.config.js /opt/cueweb/
COPY postcss.config.js /opt/cueweb/
COPY tailwind.config.js /opt/cueweb/
COPY app/ /opt/cueweb/app/
COPY components/ /opt/cueweb/components/
COPY lib/ /opt/cueweb/lib/
COPY sentry.client.config.ts /opt/cueweb/sentry.client.config.ts
COPY sentry.server.config.ts /opt/cueweb/sentry.server.config.ts
COPY sentry.edge.config.ts /opt/cueweb/sentry.edge.config.ts
COPY public/ /opt/cueweb/public/ 

# needed to give permission to store cached data from 'fetch'
RUN chmod 755 /opt/cueweb

EXPOSE 3000

# for dev testing:
# CMD ["/bin/sh"]
# command for running unit tests:
# CMD ["npm, "run", "test"]
# command for running the application
# CMD ["npm", "run", "dev"]

# For production builds using Openshift (comment out all the following lines when testing locally):
# this is required to build Next.js or else it will throw errors. Actual env variables will be passed by Openshift
ENV NEXTAUTH_URL=tobeoverriden
ENV NEXTAUTH_SECRET=tobeoverriden
ENV NEXT_JWT_SECRET=tobeoverriden
ENV NEXT_AUTH_OKTA_CLIENT_ID=tobeoverriden
ENV NEXT_AUTH_OKTA_ISSUER=tobeoverriden
ENV NEXT_AUTH_OKTA_CLIENT_SECRET=tobeoverriden
ENV SENTRY_ENVIRONMENT=tobeoverriden
ENV SENTRY_PROJECT=tobeoverriden
ENV SENTRY_URL=tobeoverriden
ENV SENTRY_ORG=tobeoverriden
ENV SENTRY_DSN=tobeoverriden
ENV LDAP_LOGIN_DN=tobeoverriden
ENV LDAP_CERTIFICATE=tobeoverriden
ENV LDAP_URI=tobeoverriden

# The following environment variables need to be accurately defined during production or dev builds as their
# values cannot be changed after build time. Use ARG to allow override at build time.
#
# NEXT_PUBLIC_URL defaults to an empty string so the client builds a
# same-origin relative URL (e.g. /api/job/getjobs) for every API call.
# That lets any other LAN client (e.g. other computer or smartphone)
# load CueWeb from the Mac's LAN IP (`http://<lan-ip>:3000`) and have
# its API calls land on the same host instead of trying to fetch from
# `localhost`, which on the phone resolves to the phone itself.
# Override at build time only if your deployment serves the API from a
# different origin than the UI.
ARG NEXT_PUBLIC_URL=
ENV NEXT_PUBLIC_URL=${NEXT_PUBLIC_URL}

ARG NEXT_PUBLIC_OPENCUE_ENDPOINT=http://localhost:8448
ENV NEXT_PUBLIC_OPENCUE_ENDPOINT=${NEXT_PUBLIC_OPENCUE_ENDPOINT}

# Optional URL template used by the Frame context menu's "View Log on
# <editor>" item. The literal `{path}` is replaced at click time with
# the absolute frame log path, and the resulting custom-URL-scheme link
# is handed to the OS so it launches the registered handler. Examples:
#   vscode://file{path}
#   vscode-insiders://file{path}
#   subl://open?url=file://{path}
#   txmt://open?url=file://{path}
#   idea://open?file={path}
# Web browsers can't read the user's $EDITOR or spawn subprocesses, so
# this URL-scheme route is the web-native equivalent of cuegui's
# popupView(file) helper. Leave empty to omit the menu item entirely
# (today's in-browser Monaco log viewer remains the default).
ARG NEXT_PUBLIC_LOG_EDITOR_URL=
ENV NEXT_PUBLIC_LOG_EDITOR_URL=${NEXT_PUBLIC_LOG_EDITOR_URL}

# Authentication providers - use ARG to allow override at build time
# Set to empty string to disable authentication (sandbox mode)
# Set to comma-separated list for production (e.g., "google,okta,github,ldap")
ARG NEXT_PUBLIC_AUTH_PROVIDER=google,okta,github,ldap
ENV NEXT_PUBLIC_AUTH_PROVIDER=${NEXT_PUBLIC_AUTH_PROVIDER}

# Build version shown in the bottom status bar. Defaults to the
# package.json version (resolved in next.config.js) when this ARG is not
# overridden at build time. CI can override with a Git SHA or build tag.
ARG NEXT_PUBLIC_APP_VERSION=
ENV NEXT_PUBLIC_APP_VERSION=${NEXT_PUBLIC_APP_VERSION}

RUN npm run build
CMD ["npm", "run", "start"]