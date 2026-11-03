FROM condaforge/miniforge3:latest AS build
COPY ./environment.yml /tmp/environment.yml
# Drop the editable pip line; install the package normally below
RUN sed -i '/pip:/,$d' /tmp/environment.yml
RUN mamba env create -p /opt/env -f /tmp/environment.yml
RUN mamba clean -afy

# Required to build some python deps. TODO: move upwards
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE /src/
COPY plannotate /src/plannotate
RUN /opt/env/bin/pip install --no-cache-dir "/src[api]"
ARG PLANNOTATE_DATABASE_SHA256=50b958f1e55119659a5df0eaafbbdfb0f34d29e3e48c8cdb8a50f9a344095589
ENV PLANNOTATE_DATABASE_SHA256=${PLANNOTATE_DATABASE_SHA256}
RUN /opt/env/bin/plannotate setupdb
# pip (and its vendored urllib3/msgpack) is only needed to build, not to run
RUN /opt/env/bin/python -m pip uninstall -y pip setuptools wheel

# distroless: no shell or package manager. Use the :debug-nonroot tag to get a busybox
# shell when troubleshooting.
FROM gcr.io/distroless/base-debian13:nonroot
COPY --from=build /opt/env /opt/env
COPY gunicorn.conf.py /app/gunicorn.conf.py
WORKDIR /app
ENV PATH=/opt/env/bin:$PATH
USER nonroot
EXPOSE 8000
# no ENTRYPOINT, so "docker run <image> plannotate batch ..." still works for the CLI
CMD ["gunicorn", "plannotate.api:app", "-c", "gunicorn.conf.py"]