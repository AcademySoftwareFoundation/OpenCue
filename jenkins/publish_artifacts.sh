#!/bin/sh

current_branch="$(git branch --remote --verbose --no-abbrev --contains | sed -rne 's/^[^\/]*\/([^\ ]+).*$/\1/p')"

if [ ! "$current_branch" = "master" ]; then
  echo "Current branch is \"${current_branch}\", not master. Skipping"
  exit 0
fi

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <BUILD_ID> <ARTIFACT_DIRECTORY>"
  exit 1
fi

build_id=$1
artifact_directory=$2

if [[ -z "${CUE_PUBLISH_BUCKET}" ]]; then
  echo "CUE_PUBLISH_BUCKET must be defined"
  exit 1
fi

if [[ -z "${CUE_PUBLISH_PROJECT}" ]]; then
  echo "CUE_PUBLISH_PROJECT must be defined"
  exit 1
fi

gsutil -m cp \
  "${artifact_directory}/build_metadata.json" \
  "${artifact_directory}/cuebot-${build_id}-all.jar" \
  "${artifact_directory}/rqd-${build_id}-all.tar.gz" \
  "${artifact_directory}/pycue-${build_id}-all.tar.gz" \
  "${artifact_directory}/pyoutline-${build_id}-all.tar.gz" \
  "${artifact_directory}/cuegui-${build_id}-all.tar.gz" \
  "gs://${CUE_PUBLISH_BUCKET}/${build_id}/"

gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin https://gcr.io

for component in cuebot rqd pycue pyoutline cuegui; do
  docker tag opencue/${component}:${build_id} gcr.io/${CUE_PUBLISH_PROJECT}/opencue-${component}:${build_id}
  docker push gcr.io/${CUE_PUBLISH_PROJECT}/opencue-${component}:${build_id}
done

