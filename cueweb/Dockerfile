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
COPY components/ui /opt/cueweb/components/ui
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

# The following environment variables need to be accurately defined during production or dev builds as their
# values cannot be changed after build time
ENV NEXT_PUBLIC_URL=tobeoverriden
ENV NEXT_PUBLIC_OPENCUE_ENDPOINT=tobeoverriden
ENV NEXT_PUBLIC_AUTH_PROVIDER=google,okta,github

RUN npm run build
CMD ["npm", "run", "start"]