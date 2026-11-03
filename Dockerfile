FROM condaforge/miniforge3:latest AS build
COPY ./environment.yml /tmp/environment.yml
# Drop the editable pip line; install the package normally below
RUN sed -i '/pip:/,$d' /tmp/environment.yml
RUN mamba env create -p /opt/env -f /tmp/environment.yml
RUN mamba clean -afy

# Required to build some python deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . /src
RUN /opt/env/bin/pip install --no-cache-dir /src
ARG PLANNOTATE_DATABASE_SHA256=50b958f1e55119659a5df0eaafbbdfb0f34d29e3e48c8cdb8a50f9a344095589
ENV PLANNOTATE_DATABASE_SHA256=${PLANNOTATE_DATABASE_SHA256}
RUN /opt/env/bin/plannotate setupdb

FROM debian:stable-slim
# or gcr.io/distroless/base-debian12 if you don't need a shell
COPY --from=build /opt/env /opt/env
ENV PATH=/opt/env/bin:$PATH
RUN useradd -m app
USER app