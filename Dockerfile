# Use a lightweight Python image
FROM python:3.11-slim

# Make Python behave nicely in containers
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Set the working directory inside the container
WORKDIR /app

# Install system-level dependencies if you need them (uncomment + edit if required)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#  && rm -rf /var/lib/apt/lists/*

# Copy dependency file first (for better layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project
COPY . .

# Create a non-root user and give it ownership of /app
RUN useradd -m appuser && chown -R appuser /app

USER appuser

# Default env var (will typically be overridden at runtime)
ENV OPENAI_API_KEY=""

# Use ENTRYPOINT so runtime arguments are forwarded to the Python module.
# This makes `docker run image --skip-embeddings` execute
# `python -m src.run_pipeline --skip-embeddings` as expected.
ENTRYPOINT ["python", "-m", "src.run_pipeline"]
# Default command-line arguments (can be overridden by `docker run <args>`)
CMD []