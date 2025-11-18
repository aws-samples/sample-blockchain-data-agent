# Use uv's official ARM64 Python base image (includes uvx)
FROM --platform=linux/arm64 ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Verify uvx is available (already included in base image)
RUN uvx --version

# Copy requirements and install Python dependencies using uv
COPY requirements.txt ./
RUN uv pip install --system --no-cache -r requirements.txt

# Copy agent code
COPY blockchain_agent_agentcore.py ./

# Expose port 8080 (AgentCore requirement)
EXPOSE 8080

# Run with opentelemetry instrumentation for observability
CMD ["opentelemetry-instrument", "python", "blockchain_agent_agentcore.py"]
