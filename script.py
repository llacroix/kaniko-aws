# Import everything that's necessary before cleaning up filesystem
import click
import os
import jedi # noqa
import json
import boto3
import requests
import encodings.idna
import encodings.cp437 # noqa
from urllib.parse import urlparse
from os.path import islink
import sys
from pathlib import Path
from shutil import rmtree
from ptpython import embed
from ptpython.style import get_all_code_styles, get_all_ui_styles
from pygments.styles import get_style_by_name # noqa
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.input.defaults import create_input
from subprocess import run
from concurrent.futures import thread # noqa
import zipfile
import logging

_logger = logging.getLogger(__name__)

s3 = boto3.client('s3')
ecr = boto3.client('ecr')

CONTEXT_DIR = "/kaniko/build"


def preload_application():
    get_all_ui_styles()
    get_all_code_styles()
    load_key_bindings()
    create_input()


def clean_folder(path):

    if islink(path):
        path.unlink()
    elif path.is_file():
        path.unlink()
    elif path.is_dir():
        rmtree(path)

    _logger.debug("Removing %s", path)


def clean_filesystem():
    safe_paths = [
        Path(x)
        for x in [
            '/dev',
            '/etc',
            '/proc',
            '/sys',
            '/tmp',
            '/var',
            '/kaniko',
            '/project',
            '/project2'
        ]
    ]

    empty_paths = [
        Path('/tmp'),
        Path('/etc'),
        Path('/var')
    ]

    for path in Path('/').iterdir():
        if path in safe_paths:
            continue
        clean_folder(path)

    for path in empty_paths:
        for p in path.iterdir():
            try:
                clean_folder(p)
            except Exception:
                pass


def get_dockerfile_path(dockerfile):
    parsed = urlparse(dockerfile)
    if not parsed.netloc:
        return Path(dockerfile)

    path = Path('/kaniko/Dockerfile')

    if parsed.scheme == 's3':
        s3.download_file(
            parsed.netloc,
            parsed.path,
            str(path)
        )
        return path
    elif parsed.scheme in ['http', 'https']:
        req = requests.get(dockerfile)
        with path.open('wb') as fout:
            fout.write(req.content)
        return path


def build_image(dockerfile="/kaniko/Dockerfile", target=None):
    params = [
        '/kaniko/executor',
        '--context', CONTEXT_DIR,
        '-f', str(dockerfile),
        '--cleanup'
    ]

    if target is None:
        params.append('--no-push')
    else:
        params += [
            '--destination', target
        ]

    return run(params)


def docker_login():
    auths = ecr.get_authorization_token()

    token = auths['authorizationData'][0]

    url = urlparse(token['proxyEndpoint'])

    data = {
        'auths': {
            url.netloc: {
                "auth": token['authorizationToken']
            }
        }
    }

    docker_file = Path('/kaniko/.docker/config.json')
    with docker_file.open('w') as fout:
        fout.write(json.dumps(data))


def create_build_context(bucket, object_name):
    build_path = Path(CONTEXT_DIR)

    if build_path.exists():
        rmtree(build_path)

    build_path.mkdir()

    if bucket and object_name:
        s3.download_file(bucket, object_name, '/tmp/build.zip')

        with zipfile.ZipFile('/tmp/build.zip', 'r') as zip_ref:
            zip_ref.extractall(str(build_path))

        Path('/tmp/build.zip').unlink()


def automated_build(dockerfile_path, bucket, data_object, repo):
    create_build_context(bucket, data_object)
    docker_login()
    build_image(dockerfile_path, target=repo)
    return 0


def interactive_main():
    return embed(globals(), locals())


@click.command()
@click.option(
    '--interactive',
    is_flag=True,
    default=False
)
@click.option(
    '--bucket',
    help="S3 Bucket for data",
)
@click.option(
    '--context-object',
    help="S3 Object containing context data",
)
@click.option(
    '--repo',
    help="Destination Repository"
)
@click.argument(
    'dockerfile'
)
def main(interactive, bucket, context_object, repo, dockerfile):
    is_running_in_docker = os.environ.get('I_AM_RUNNING_IN_DOCKER', False)

    if not is_running_in_docker:
        print("Do not run this outside of docker.")
        sys.exit(1)

    if not bucket:
        bucket = os.environ.get('S3_BUCKET')

    if not context_object:
        context_object = os.environ.get('S3_OBJECT')

    if not repo:
        repo = os.environ.get('ECR_REPO')

    preload_application()
    clean_filesystem()

    dockerfile_path = get_dockerfile_path(dockerfile)

    if interactive:
        ret = interactive_main(bucket, context_object, repo)
    else:
        ret = automated_build(dockerfile_path, bucket, context_object, repo)

    sys.exit(ret)


main()
