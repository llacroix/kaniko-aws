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


def get_resource(uri, target):
    """
    Get a resource from s3 or http and store it in
    the target path.
    """
    parsed = urlparse(uri)
    path = Path(target)

    if parsed.scheme == 's3':
        print(
            "Getting file from s3: {} {}".format(
                parsed.netloc, parsed.path[1:]
            )
        )
        s3.download_file(
            parsed.netloc,
            parsed.path[1:],
            str(path)
        )

        return path
    elif parsed.scheme in ['http', 'https']:
        print("Getting file from http: {}".format(uri))
        req = requests.get(uri)
        with path.open('wb') as fout:
            fout.write(req.content)

        return path


def get_dockerfile(dockerfile):
    parsed = urlparse(dockerfile)
    if not parsed.netloc:
        return Path(dockerfile)

    path = Path('/kaniko/Dockerfile')

    return get_resource(dockerfile, path)


def get_context(uri):
    parsed = urlparse(uri)
    if not parsed.netloc:
        return Path(uri)

    context_zip = get_resource(uri, Path("/tmp/context.zip"))

    path = Path("/kaniko/context")

    with zipfile.ZipFile(str(context_zip), 'r') as zip_ref:
        zip_ref.extractall(str(path))

    context_zip.unlink()

    return path


def build_image(
    dockerfile="/kaniko/Dockerfile",
    context=None,
    destination=None
):
    params = [
        '/kaniko/executor',
        '--cleanup',
        '-f', str(dockerfile),
    ]

    if context:
        params += [
            '--context', str(context)
        ]

    if destination is None:
        params.append('--no-push')
    else:
        params += [
            '--destination', destination
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


def automated_build(
    dockerfile,
    dockerfile_path,
    context,
    context_path,
    destination
):
    docker_login()
    build_image(
        dockerfile_path,
        context=context_path,
        destination=destination
    )
    return 0


def interactive_main(
    dockerfile,
    dockerfile_path,
    context,
    context_path,
    destination
):
    return embed(globals(), locals())


@click.command()
@click.option(
    '--interactive',
    is_flag=True,
    default=False
)
@click.option(
    '-c',
    '--context',
    help=(
        "URL or Path to context. It can use url of with the "
        "s3, http and https scheme."
    )
)
@click.option(
    '-d',
    '--destination',
    help="Destination Image"
)
@click.argument(
    'dockerfile'
)
def main(interactive, context, destination, dockerfile):
    is_running_in_docker = os.environ.get('I_AM_RUNNING_IN_DOCKER', False)

    if not is_running_in_docker:
        print("Do not run this outside of docker.")
        sys.exit(1)

    if not context:
        context = os.environ.get('CONTEXT')

    if not destination:
        destination = os.environ.get('DESTINATION_IMAGE')

    preload_application()
    clean_filesystem()

    dockerfile_path = get_dockerfile(dockerfile)
    context_path = get_context(context)

    if not dockerfile_path:
        sys.exit(2)

    if interactive:
        ret = interactive_main(
            dockerfile,
            dockerfile_path,
            context,
            context_path,
            destination
        )
    else:
        ret = automated_build(
            dockerfile,
            dockerfile_path,
            context,
            context_path,
            destination
        )

    sys.exit(ret)


main()
