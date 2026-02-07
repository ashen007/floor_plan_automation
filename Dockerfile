# Use NVIDIA CUDA base image with Ubuntu
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    vim \
    build-essential \
    libboost-all-dev \
    libeigen3-dev \
    libsuitesparse-dev \
    libfreeimage-dev \
    libgoogle-glog-dev \
    libgflags-dev \
    libglew-dev \
    qtbase5-dev \
    libqt5opengl5-dev \
    libcgal-dev \
    libcgal-qt5-dev \
    python3.10 \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1
RUN update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Install PyTorch with CUDA support
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Install tiny-cuda-nn (pre-compile to avoid runtime compilation)
RUN pip install ninja
RUN pip install git+https://github.com/NVlabs/tiny-cuda-nn/#subdirectory=bindings/torch

# Install COLMAP (for 3D reconstruction)
RUN apt-get update && apt-get install -y \
    colmap \
    && rm -rf /var/lib/apt/lists/*

# Install nerfstudio
RUN pip install nerfstudio

# Install additional dependencies for floor plan generation
RUN pip install \
    trimesh \
    pillow \
    numpy \
    scipy \
    matplotlib

# Create directories
RUN mkdir -p /workspace/data /workspace/output /workspace/scripts

# Copy the pipeline script
COPY floorplan_pipeline_docker.py /workspace/scripts/floorplan_pipeline.py

# Set environment variables
ENV CUDA_HOME=/usr/local/cuda
ENV PATH="${CUDA_HOME}/bin:${PATH}"
ENV LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}"

# Expose viewer port for nerfstudio
EXPOSE 7007

# Default command
CMD ["/bin/bash"]