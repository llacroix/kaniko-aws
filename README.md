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
