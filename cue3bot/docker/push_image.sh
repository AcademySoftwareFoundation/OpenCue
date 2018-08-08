#!/bin/sh

set -e

GCP_PROJECT=queue-manager-dev


# If you've already built the image, this should use the Docker cache and
# finish very quickly.
$(dirname $0)/build_image.sh

gcloud --project $GCP_PROJECT docker -- push gcr.io/$GCP_PROJECT/cuebot:${USER}
