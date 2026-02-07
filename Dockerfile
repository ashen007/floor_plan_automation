# Use official nerfstudio image (version 0.3.4 - stable)
FROM dromni/nerfstudio:0.3.4

# Switch to root for system installations
USER root

WORKDIR /workspace

# Install additional dependencies for floor plan generation
RUN pip install trimesh pillow

# Install COLMAP if not included
RUN apt-get update && apt-get install -y colmap && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /workspace/data /workspace/output /workspace/scripts

# Copy the pipeline script
COPY floorplan_pipeline_docker.py /workspace/scripts/floorplan_pipeline.py

# Switch back to user (if base image has one)
# Uncomment if needed: USER user

# Expose viewer port
EXPOSE 7007

CMD ["/bin/bash"]