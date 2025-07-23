FROM ubuntu:22.04

LABEL authors="Roberto Del Prete"
LABEL maintainer="roberto.delprete@esa.int"

USER root

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

ENV LC_ALL "en_US.UTF-8"

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
RUN pdm run python -m ipykernel install --user --name=phidown --display-name="Phidown"

# Create a startup script
RUN echo '#!/bin/bash\n\
cd /workspace\n\
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token="" --NotebookApp.password=""' > /usr/local/bin/start-jupyter.sh

RUN chmod +x /usr/local/bin/start-jupyter.sh

EXPOSE 8888

CMD ["/usr/local/bin/start-jupyter.sh"]