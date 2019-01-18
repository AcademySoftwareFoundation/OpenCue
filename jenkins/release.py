#!/usr/bin/env python

# Script for publishing a public release from an OpenCue build.
#
# Depends on the `requests` library, which you can install via pip:
#
# pip install requests
#
# This script calls the GitHub API and needs a Personal Access Token to be
# provided via the GITHUB_TOKEN environment variable. You can create this
# token via the GitHub UI or on the commandline like:
#
# curl \
#  -u 'username' \
#  -d '{"scopes":["repo"], "note":"OpenCue release script"}' \
#  https://api.github.com/authorizations
#
# If you use multi-factor authentication you can provide that via a header
# like:
#
# curl \
#  -u 'username' \
#  -H 'X-GitHub-OTP: 000000' \
#  -d '{"scopes":["repo"], "note":"OpenCue release script"}' \
#  https://api.github.com/authorizations
#
# This script ALSO pushes Docker images to Docker Hub as part of its release
# process. For this to work you need your local Docker client to be logged
# in as a user with access to the Docker hub org.
#
# docker login --username=$DOCKER_HUB_USER

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile

import requests


BUILD_ID_RE = re.compile('^\d+\.\d+\.\d+$')
GITHUB_API = 'https://api.github.com'
REPO = 'imageworks/OpenCue'
DOCKER_IMAGES = ['cuebot', 'rqd', 'pycue', 'pyoutline', 'cuegui', 'cuesubmit']
DOCKERHUB_ORG = 'opencue'


def _release_exists(release_tag):
  response = requests.get(
      '%s/repos/%s/releases/tags/%s' % (GITHUB_API, REPO, release_tag),
      headers={'Authorization': 'token %s' % os.environ['GITHUB_TOKEN']})
  if response.status_code == 200:
    return True
  elif response.status_code == 404:
    return False
  else:
    raise Exception(
        'Unexpected response checking for release %s. Error code [%d], error [%s]' % (
            release_tag, response.status_code, response.text))


def _get_release(release_tag):
  response = requests.get(
      '%s/repos/%s/releases/tags/%s' % (GITHUB_API, REPO, release_tag),
      headers={'Authorization': 'token %s' % os.environ['GITHUB_TOKEN']})
  if response.status_code == 200:
    return response.json()
  else:
    raise Exception(
        'Failed to find release %s. Error code [%d], error [%s]' % (
            release_tag, response.status_code, response.text))


def _create_release(release_tag, build_metadata):
  response = requests.post(
      '%s/repos/%s/releases' % (GITHUB_API, REPO),
      headers={'Authorization': 'token %s' % os.environ['GITHUB_TOKEN']},
      json={
          'tag_name': release_tag,
          'target_commitish': build_metadata['git_commit'],
          'name': release_tag,
          # TODO(bcipriano) Construct changelog from commits since the last release.
          # https://github.com/imageworks/OpenCue/issues/106
          'body': 'OpenCue %s' % release_tag,
          'draft': False,
          'prerelease': False,
      })
  if response.status_code not in (200, 201):
    raise Exception(
        'Failed to create GitHub release. Code [%d], error: [%s]' % (
            response.status_code, response.text))
  return response.json()


def _upload_artifact(artifact_file, release):
  print 'Uploading artifact %s...' % os.path.basename(artifact_file)
  if _artifact_exists(artifact_file, release):
    print 'Artifact already uploaded'
  else:
    _, ext = os.path.splitext(artifact_file)
    if ext == '.gz':
      content_type = 'application/gzip'
    elif ext == '.jar':
      content_type = 'application/java-archive'
    else:
      raise Exception('Artifact %s has an unknown file type' % os.path.basename(artifact_file))
    upload_url = release['upload_url'].replace(
        '{?name,label}', '?name=%s' % os.path.basename(artifact_file))
    response = requests.post(
        upload_url,
        headers={
            'Authorization': 'token %s' % os.environ['GITHUB_TOKEN'],
            'Content-Type': content_type,
        },
        data=open(artifact_file).read())
    if response.status_code not in (200, 201):
      raise Exception(
          'Failed to upload release artifact %s. Code [%d], error: [%s]' % (
              os.path.basename(artifact_file), response.status_code, response.text))


def _artifact_exists(artifact_file, release):
  response = requests.get(
      '%s/repos/%s/releases/%s/assets' % (GITHUB_API, REPO, release['id']),
      headers={'Authorization': 'token %s' % os.environ['GITHUB_TOKEN']})
  if response.status_code != 200:
    raise Exception(
        'Failed to list release artifacts for release ID %s. Code [%d], error: [%s]' % (
            release['id'], response.status_code, response.text))
  asset_list = response.json()
  return any([asset['name'] == os.path.basename(artifact_file) for asset in asset_list])


def _get_gcr_image_uri(image_name, build_id):
  return 'gcr.io/%s/opencue-%s:%s' % (os.environ['CUE_PUBLISH_PROJECT'], image_name, build_id)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--build_id', required=True, help='Build ID to release')
  args = parser.parse_args()

  # Verify build ID is valid. This also forces releases to come from the master branch -
  # other branches append a commit hash to the build ID.
  if not BUILD_ID_RE.match(args.build_id):
    raise Exception('Invalid build ID %s' % args.build_id)

  req_env_vars = ['GITHUB_TOKEN', 'CUE_PUBLISH_BUCKET', 'CUE_PUBLISH_PROJECT']
  for req_env_var in req_env_vars:
    if req_env_var not in os.environ:
      raise Exception('Environment var %s is required and was not found' % req_env_var)

  tmpdir = tempfile.mkdtemp()
  print 'Using temp directory %s' % tmpdir

  print 'Collecting build artifacts from GCS...'
  cmd = [
      'gsutil', '-m', 'cp',
      'gs://%s/%s/*' % (os.environ['CUE_PUBLISH_BUCKET'], args.build_id),
      '%s/' % tmpdir]
  subprocess.check_call(cmd)

  release_artifacts = os.listdir(tmpdir)
  if not release_artifacts:
    raise Exception('No release artifacts were found')

  if 'build_metadata.json' not in release_artifacts:
    raise Exception('Build metadata was not found alongside build artifacts')

  with open(os.path.join(tmpdir, 'build_metadata.json')) as fp:
    build_metadata = json.load(fp)

  print 'Collecting docker images from GCR...'
  subprocess.check_call(['gcloud', 'auth', 'configure-docker', '--quiet'])
  for docker_image in DOCKER_IMAGES:
    cmd = ['docker', 'pull', _get_gcr_image_uri(docker_image, args.build_id)]
    subprocess.check_call(cmd)

  release_tag = 'v%s' % args.build_id
  if _release_exists(release_tag):
    print 'Found release %s' % release_tag
    release = _get_release(release_tag)
  else:
    print 'Creating new release %s...' % release_tag
    release = _create_release(release_tag, build_metadata)

  for release_artifact in release_artifacts:
    if release_artifact == 'build_metadata.json':
      continue
    _upload_artifact(os.path.join(tmpdir, release_artifact), release)

  print 'Pushing Docker images to Docker hub...'
  for docker_image in DOCKER_IMAGES:
    dockerhub_uri = '%s/%s:%s' % (DOCKERHUB_ORG, docker_image, args.build_id)
    cmds = [
        ['docker', 'tag', _get_gcr_image_uri(docker_image, args.build_id), dockerhub_uri],
        ['docker', 'push', dockerhub_uri],
    ]
    for cmd in cmds:
      subprocess.check_call(cmd)

  shutil.rmtree(tmpdir)


if __name__ == '__main__':
  main()

