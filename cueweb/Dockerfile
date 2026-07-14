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
# Retry on transient registry network errors (ECONNRESET / aborted) instead of
# failing the build on the first blip. CI runners hit these intermittently.
RUN npm ci \
      --fetch-retries=5 \
      --fetch-retry-factor=2 \
      --fetch-retry-mintimeout=20000 \
      --fetch-retry-maxtimeout=120000 \
      --fetch-timeout=600000

COPY *.json /opt/cueweb/
COPY OVERRIDE_CUEWEB_VERSION.in /opt/cueweb/
# Repo-root VERSION.in (OpenCue's shared version) read by next.config.js when
# OVERRIDE_CUEWEB_VERSION.in is set to the "VERSION.in" sentinel. It lives
# outside this build context, so it is pulled from the `project_root` named
# build context (defined in docker-compose.yml; for a standalone build pass
# `--build-context project_root=<repo-root>`).
COPY --from=project_root VERSION.in /opt/VERSION.in
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

# CueProgBar launcher (Monitor Jobs "Show Progress Bar"). CueProgBar is a
# desktop tool (python -m cuegui.cueguiplugin.cueprogbar <job>); a browser
# can only reach it via a registered URL scheme. {job} is replaced with the
# job name. Leave empty to fall back to the in-table Progress column.
ARG NEXT_PUBLIC_CUEPROGBAR_URL=
ENV NEXT_PUBLIC_CUEPROGBAR_URL=${NEXT_PUBLIC_CUEPROGBAR_URL}

# The CueProgBar command shown in the "Show Progress Bar" dialog. {job} is
# replaced with the job name. Sites override this with their own launcher,
# e.g. "spawn launch cueprogbar {job}".
ARG NEXT_PUBLIC_CUEPROGBAR_COMMAND=python -m cuegui.cueguiplugin.cueprogbar {job}
ENV NEXT_PUBLIC_CUEPROGBAR_COMMAND=${NEXT_PUBLIC_CUEPROGBAR_COMMAND}

# "Preview All" (Frames menu) opens rendered output in an external image
# viewer. PREVIEW_COMMAND is the command shown/copied; PREVIEW_URL is an
# optional registered URL scheme the Launch button hands off to a local
# handler. Placeholders {paths} (output paths), {job}, {layer}, {frame} are
# substituted. Override per site, e.g. a viewer scheme "openrv://{paths}".
ARG NEXT_PUBLIC_PREVIEW_COMMAND=rv {paths}
ENV NEXT_PUBLIC_PREVIEW_COMMAND=${NEXT_PUBLIC_PREVIEW_COMMAND}
ARG NEXT_PUBLIC_PREVIEW_URL=
ENV NEXT_PUBLIC_PREVIEW_URL=${NEXT_PUBLIC_PREVIEW_URL}

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

# Build SHA shown in the About CueWeb dialog. CI injects the short Git SHA via
# --build-arg NEXT_PUBLIC_GIT_SHA=$(git rev-parse --short HEAD). Empty -> "unknown".
ARG NEXT_PUBLIC_GIT_SHA=
ENV NEXT_PUBLIC_GIT_SHA=${NEXT_PUBLIC_GIT_SHA}

RUN npm run build
CMD ["npm", "run", "start"]