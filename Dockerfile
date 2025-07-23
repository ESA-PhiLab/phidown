FROM ubuntu:22.04 as base

RUN apt-get update && apt-get install -y openjdk-8-jdk && rm -rf /var/lib/apt/lists/*

FROM base as build

LABEL authors="Roberto Del Prete"
LABEL maintainer="roberto.delprete@esa.int"

USER root

RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    python3 \
    python3-pip \
    git \
    vim \
    fontconfig \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

ENV LC_ALL "en_US.UTF-8"
ENV LD_LIBRARY_PATH ".:/usr/lib/jvm/java-8-openjdk-amd64/jre/lib/amd64/server/:$LD_LIBRARY_PATH"
ENV JAVA_HOME "/usr/lib/jvm/java-8-openjdk-amd64"

# Download and install SNAP directly
RUN wget -q https://download.esa.int/step/snap/11.0/installers/esa-snap_sentinel_linux-11.0.0.sh -O /tmp/snap_installer.sh && \
    chmod +x /tmp/snap_installer.sh && \
    /tmp/snap_installer.sh -q -dir /usr/local/snap && \
    rm /tmp/snap_installer.sh

FROM base as jupyter-ready

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    fonts-dejavu \
    git \
    build-essential \
    pkg-config \
    libzstd-dev \
    gcc \
    g++ \
    clang \
    make \
    cmake \
    libc6-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV LD_LIBRARY_PATH ".:$LD_LIBRARY_PATH"
ENV JAVA_HOME "/usr/lib/jvm/java-8-openjdk-amd64"
ENV PATH="${PATH}:/usr/local/snap/bin"

COPY --from=build /usr/local/snap /usr/local/snap

# Create symlink for python command
RUN ln -s /usr/bin/python3 /usr/bin/python

# Copy project files
COPY pyproject.toml /workspace/
COPY pdm.lock /workspace/
COPY phidown /workspace/phidown/
COPY README.md /workspace/
COPY LICENSE /workspace/

WORKDIR /workspace

# Install the package and Jupyter
RUN pip install pdm jupyter jupyterlab ipykernel
RUN pdm sync --dev

# Install phidown as a Jupyter kernel
RUN pdm run python -m ipykernel install --user --name=phidown --display-name="Phidown (SNAP-11.0)"

# Create a startup script
RUN echo '#!/bin/bash\n\
export JAVA_HOME="/usr/lib/jvm/java-8-openjdk-amd64"\n\
export LD_LIBRARY_PATH=".:$LD_LIBRARY_PATH"\n\
export PATH="${PATH}:/usr/local/snap/bin"\n\
cd /workspace\n\
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token="" --NotebookApp.password=""' > /usr/local/bin/start-jupyter.sh

RUN chmod +x /usr/local/bin/start-jupyter.sh

EXPOSE 8888

CMD ["/usr/local/bin/start-jupyter.sh"]