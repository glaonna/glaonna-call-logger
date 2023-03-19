# We use full Debian to be able to compile uptime & psutil
FROM python:3.11-bullseye as builder

# Install the package dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
COPY requirements.txt /requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip --disable-pip-version-check install --no-compile -r /requirements.txt

# Install the package itself
COPY pyproject.toml LICENSE README.md /project/
COPY src /project/src/
RUN pip --disable-pip-version-check install --no-cache-dir --no-compile --no-clean --no-deps /project


# syntax=docker/dockerfile:1.2
FROM python:3.11-slim-bullseye as base

# Add Labels for OCI Image Format Specification
LABEL org.opencontainers.image.vendor="Quartx"
LABEL org.opencontainers.image.authors="William Forde"

# Build Arguments, used to pass in Environment Variables
ARG VERSION="latest"
ARG SENTRY_DSN=""
ARG REG_KEY=""

# Docker Environment Variables
ENV PYTHONUNBUFFERED=1
ENV DOCKERIZED=1
ENV ENVIRONMENT="Dockerized"
ENV DATA_LOCATION="/data"
ENV SENTRY_DSN=$SENTRY_DSN
ENV REG_KEY=$REG_KEY
ENV VIRTUAL_ENV=/opt/venv
ENV VERSION=$VERSION

# Image setup
RUN mkdir -p $DATA_LOCATION && \
    useradd -rm -d /home/runner -s /bin/bash -g users -G dialout -u 999 runner && \
    chown runner:users $DATA_LOCATION
WORKDIR /home/runner

# Copy required scripts
COPY data/99-serial.rules /etc/udev/rules.d/99-serial.rules
COPY data/entrypoint.sh /entrypoint.sh

# Finalize build image
COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENTRYPOINT ["/entrypoint.sh"]
CMD ["calllogger"]
USER runner:users
