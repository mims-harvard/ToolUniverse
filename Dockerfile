FROM python:3.12-slim

WORKDIR /app

# Install build dependencies and runtime libraries for packages that need them
RUN apt-get update && apt-get install -y --no-install-recommends \
  gcc \
  g++ \
  libxrender1 \
  libxext6 \
  libsm6 \
  libx11-6 \
  libexpat1 \
  && rm -rf /var/lib/apt/lists/*

# Install tooluniverse from PyPI
RUN pip install --no-cache-dir tooluniverse

# Remove build dependencies to reduce image size (keep runtime libraries)
RUN apt-get purge -y gcc g++ && apt-get autoremove -y

# Set environment variable to reduce verbosity (optional)
ENV TOOLUNIVERSE_LOG_LEVEL=WARNING

# Run the MCP server with stdio transport
# TOOLUNIVERSE_STDIO_MODE=1 is automatically set by tooluniverse-smcp-stdio
CMD ["tooluniverse-smcp-stdio"]

