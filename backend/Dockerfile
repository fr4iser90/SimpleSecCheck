# Stage 1: Base Python image and core dependencies
FROM python:3.11-slim-bullseye AS base

# Set environment variables to ensure Python output is sent straight to terminal
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PATH="/root/.local/bin:$PATH"

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for Python packages (e.g., psycopg2, Pillow)
# Keep this minimal; add more as identified by package installation failures.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    postgresql-client \
    # For Pillow (if image processing is needed)
    # libjpeg-dev zlib1g-dev libtiff-dev libfreetype6-dev liblcms2-dev libwebp-dev \
    # For other common Python packages
    # libffi-dev libssl-dev \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry (Python package manager)
ARG POETRY_VERSION=1.7.1
RUN pip install "poetry==${POETRY_VERSION}"

# Disable Poetry virtualenvs so binaries are available globally
RUN poetry config virtualenvs.create false

# Copy only the files necessary for installing dependencies with Poetry
COPY ./poetry.lock ./pyproject.toml /app/

RUN poetry lock

# Install project dependencies using Poetry
# --no-root: Do not install the project itself as editable, only its dependencies
# --no-dev: Do not install development dependencies (for a leaner production image)
RUN poetry install --no-root --no-dev

# Stage 2: Application code and runtime setup (can be same as base or a new stage)
# For simplicity here, we continue from the base stage.
# FROM base AS runtime

# Copy the rest of the backend application code into the working directory
COPY . /app/

# Create a non-root user for running the application for better security
# ARG APP_USER=appuser
# RUN useradd -ms /bin/bash ${APP_USER}
# RUN chown -R ${APP_USER}:${APP_USER} /app
# USER ${APP_USER}
# Note: If using a non-root user, ensure entrypoint.sh and Gunicorn/Celery can run as this user,
# and that file permissions (especially for media/static volumes) are handled correctly.
# For simplicity in this initial plan, we will run as root, but a non-root user is recommended for production.

# Expose the port Gunicorn will run on (same as in docker-compose.yml)
EXPOSE 8000

# The entrypoint script will handle migrations and then execute the CMD
# CMD is defined in the docker-compose.yml for each service (backend, worker, beat)
ENTRYPOINT ["/app/entrypoint.sh"] 