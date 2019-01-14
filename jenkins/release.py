#!/usr/bin/env python

# pip install requests

# Need a personal access token. Generate one with:
# curl \
#  -u 'username' \
#  -H 'X-GitHub-OTP: 000000' \
#  -d '{"scopes":["repo"], "note":"Publishing an OpenCue release"}' \
#  https://api.github.com/authorizations

# Store "token" field from JSON response to GITHUB_TOKEN

import argparse
import os
import subprocess
import tempfile

import requests


GITHUB_API = 'https://api.github.com'
REPO = 'imageworks/OpenCue'


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


def _create_release(release_tag):
  response = requests.post(
      '%s/repos/%s/releases' % (GITHUB_API, REPO),
      headers={'Authorization': 'token %s' % os.environ['GITHUB_TOKEN']},
      json={
          'tag_name': release_tag,
          # TODO: pull from metadata artifact
          'target_commitish': 'master',
          'name': release_tag,
          # TODO: pull changelog from metadata artifact
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
        data={os.path.basename(artifact_file): open(artifact_file).read()})
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


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--build_id', required=True, help='Build ID to release')
  args = parser.parse_args()

  req_env_vars = ['GITHUB_TOKEN', 'CUE_PUBLISH_BUCKET']
  for req_env_var in req_env_vars:
    if req_env_var not in os.environ:
      raise Exception('Environment var %s is required and was not found' % req_env_var)

  # TODO build id is from master only - \d.\d.\d

  tmpdir = tempfile.mkdtemp()

  cmd = [
      'gsutil', '-m', 'cp',
      'gs://%s/%s/*' % (os.environ['CUE_PUBLISH_BUCKET'], args.build_id),
      '%s/' % tmpdir]
  subprocess.check_call(cmd)

  release_artifacts = os.listdir(tmpdir)
  if not release_artifacts:
    raise Exception('No release artifacts were found')

  release_tag = 'v%s-test' % args.build_id

  if _release_exists(release_tag):
    print 'Found release %s' % release_tag
    release = _get_release(release_tag)
  else:
    print 'Creating new release %s...' % release_tag
    release = _create_release(release_tag)

  for release_artifact in release_artifacts:
    _upload_artifact(os.path.join(tmpdir, release_artifact), release)

  # TODO remove tmp files


if __name__ == '__main__':
  main()

