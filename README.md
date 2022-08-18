Kaniko AWS
==========

Kaniko AWS is a custom image based on kaniko that is designed to work with AWS.

- The dockerfile can be fetched from local, S3 or anywhere with HTTP.
- The build context can be fetched from S3.
- Then the resulting image is pushed to an ECR endpoint.

Requirements:
=============

You need an AWS account and credentials that can pull data from s3 and
push docker image to the destination image. The context data has to be stored
in s3 as a zip file.

How to use:
===========

First, you have to push a dockerfile to s3 or have an url from which it can be fetched. 
If it was stored on s3, you can use the url to the file if it's publicly available, or
you can use the s3 uri to the file, or you can use a presigned url that gives read access
to the dockerfile.

Then if you have to build the docker image with some context data. You have to push that
data in a zip file on s3 and pass the file to the builder using environment variable or
passing `--bucket` and `--context-object`. 

You need to set environment variables for AWS and define the region in which the ECR image
will be stored.

    docker run -it \
        -e AWS_DEFAULT_REGION=$AWS_REGION \
        -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY \
        -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET \
        llacroix/kaniko-aws:latest
            --context $CONTEXT_URI \
            --destination $DESTINATION_IMAGE \
            $DOCKERFILE_URI


Environment Variables:
======================

Variable                  | Usage                              
------------------------- | ------------------------------------
`AWS_ACCESS_KEY_ID`       | Authenticate to AWS
`AWS_SECRET_ACCESS_KEY_ID`| Authenticate to AWS
`AWS_DEFAULT_REGION`      | In which region the ECR registry is
`CONTEXT`                 | Context URI or local path to the context data
`DESTINATION_IMAGE`       | Destination to push ECR

Dockerfile Example:

    FROM ubuntu:22.04

    RUN set -x; \
        apt-get update && \
        apt-get install -y python3 python3-pip \

    COPY . /project

    RUN /usr/bin/python3 -m pip -r /project/requirements.txt

    ENTRYPOINT ["/usr/bin/python3", "/project/scripts/main.py"]
    CMD []
    
    
Then you only have to provide the necessary files in the context data to build your project without having
to make completely custom dockerfiles. It's particularly useful in a context where the only changes in
the build context are for example custom modules that you'd want to have inside an application.

This way you can automate building relatively complex applications without increasing the complexity
of the build process. Dockerfile can be reused instead of having to maintain dockerfiles within
each single projects.

How to use it on AWS:
=====================

If you were looking to use this with AWS Lambda, you're going to be a bit deceived. The reason why
it can't work with AWS lambda is because the AWS lambda filesystem is readonly. Kaniko's principle
is to modify the filesystem and watch the changes made to it. For that reason, it's simply not
possible to run kaniko with AWS Lambda.

That being said, it's possible to use this with AWS Fargate or even just spawning services using EC2
instances.

All you need to do is to create a task definition with a container running this image. Then you can
use this python script as an example on how to run it. Then you'll need some execution roles with
some available policy to be able to read from s3 and push to s3 and push to ecr.


    import boto3

    ecs = boto3.client('ecs')

    # VPC Info
    subnets = [...]
    security_groups = [...]

    # Build params
    context = "context on s3"
    destination = "image_name_on_ecr"
    dockerfile = "dockerfile on s3"

    # Task info/cluster
    cluster_name = "kaniko-cluster"
    task_def = "kaniko"

    return ecs.run_task(
        cluster=cluster_name,
        count=1,
        launchType='FARGATE',
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets': subnets,
                'securityGroups': security_groups
                'assignPublicIp': 'DISABLED'
            }
        },
        overrides={
            'containerOverrides': [
                {
                    'name': "builder",
                    "command": [
                        "--context",
                        context,
                        "--destination",
                        destination,
                        dockerfile
                    ],
                }
            ],
        },
        taskDefinition=task_def
    )
