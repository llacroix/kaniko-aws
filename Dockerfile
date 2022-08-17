from gcr.io/kaniko-project/executor:latest as kaniko
from ubuntu:22.04

# Copy kaniko data to this image
copy --from=kaniko /kaniko /kaniko                                                                                         
copy script.py /kaniko/app/script.py
copy requirements.txt /kaniko/app/requirements.txt

# Prepare application
RUN apt-get update && \
    apt-get install -y ca-certificates python3 python3-pip && \
    /usr/bin/python3 -m pip install -t /kaniko/app -r /kaniko/app/requirements.txt && \
    cp -r /etc/ssl/certs/* /kaniko/ssl/certs && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /root/.cache

# Prepare environment
ENV PATH=/usr/local/bin:/kaniko:/usr/bin
ENV HOME=/root
ENV USER=root
ENV SSL_CERT_DIR=/kaniko/ssl/certs
ENV DOCKER_CONFIG=/kaniko/.docker/
ENV DOCKER_CREDENTIAL_GCR_CONFIG=/kaniko/.config/gcloud/docker_credential_gcr_config.json
ENV I_AM_RUNNING_IN_DOCKER=true

# Start application
entrypoint ["/usr/bin/python3", "/kaniko/app/script.py"]
cmd []
