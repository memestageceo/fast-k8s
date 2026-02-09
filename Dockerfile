FROM python:3.12-slim

WORKDIR /app

# copy only dependency files first (layer caching)
COPY pyproject.toml uv.lock* ./

# install uv
RUN pip install uv

# Install deps
RUN uv pip install --system fastapi "fastapi[standard]"

# copy source
COPY . .

EXPOSE 8000

CMD [ "fastapi", "run", "main.py", "--host", "0.0.0.0" ]
