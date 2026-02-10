FROM python:3.12-slim

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy only dependency files first (for better layer caching)
COPY --chown=appuser:appuser pyproject.toml uv.lock* ./

# Install uv and dependencies
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache fastapi "fastapi[standard]" jinja2

# Copy application source code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

EXPOSE 8000

# Use exec form for proper signal handling
CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0"]
