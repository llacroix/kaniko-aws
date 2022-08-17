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

To create a docker image, it's as simple as calling this command line locally:

    docker run -it -e AWS_DEFAULT_REGION=[region] -e AWS_ACCESS_KEY_ID=[secret] -e AWS_SECRET_ACCESS_KEY=[secret] kaniko-aws:latest s3://[bucket]/[object] 


The dockerfile also take as parameter an url or a local path. It's possible for example to pass a presigned s3 url.


Environment Variables:
======================

Variable                  | Usage                              
------------------------- | ------------------------------------
`AWS_ACCESS_KEY_ID`       | Authenticate to AWS
`AWS_SECRET_ACCESS_KEY_ID`| Authenticate to AWS
`AWS_DEFAULT_REGION`      | In which region the ECR registry is
`ECR_IMAGE`               | Name of the ECR destination image
`S3_BUCKET`               | Bucket for the build context
`S3_OBJECT`               | Object name of the build context

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
