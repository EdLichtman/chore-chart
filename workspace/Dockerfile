FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    python3 \
    python3-pip \
    nodejs \
    npm \
    dotnet-sdk-8.0 \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Set working directory
WORKDIR /workspace

# Create a non-root user for safety
RUN useradd -m claude && chown -R claude:claude /workspace
USER claude

# Default command: interactive bash
CMD ["bash"]
