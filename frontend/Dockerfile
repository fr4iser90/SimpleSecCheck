# Stage 1: Build the Vue.js application
# Use an official Node.js LTS (Long Term Support) image as the base for building.
# Alpine versions are smaller. Choose one that matches your project's Node.js version needs.
FROM node:18-alpine AS builder

# Set the working directory in the container for the frontend app
WORKDIR /app/frontend

# Copy package.json and lock files, then run `npm ci` (or yarn equivalent).
COPY ./package.json ./package-lock.json* ./yarn.lock* ./
# The `*` is to handle cases where lock files might not exist initially or one is preferred.

# Install dependencies based on the lock file
# If using npm:
RUN npm ci
# If using yarn:
# RUN yarn install --frozen-lockfile

# Copy the rest of the frontend application code
COPY . .

# Build the Vue.js application for production
# This command might vary based on your Vue project setup (e.g., Vue CLI, Vite)
RUN npm run build
# If using yarn:
# RUN yarn build

# At this point, the /app/frontend/dist directory (or similar, e.g., /app/frontend/build)
# contains the compiled static assets of the Vue.js application.

# Stage 2: (Optional) Serve with Nginx directly from a leaner image
# This stage is useful if you want this Dockerfile to produce a self-contained Nginx image
# serving the frontend. Alternatively, the nginx service in docker-compose.yml can
# directly mount or copy assets from the 'builder' stage if configured appropriately.

# FROM nginx:1.25-alpine

# Copy the built static assets from the 'builder' stage
# COPY --from=builder /app/frontend/dist /usr/share/nginx/html

# Copy a custom Nginx configuration file (if needed for this specific frontend serving setup)
# COPY ./nginx/nginx-frontend-specific.conf /etc/nginx/conf.d/default.conf

# Expose port 80 for Nginx
# EXPOSE 80

# Default command to start Nginx
# CMD ["nginx", "-g", "daemon off;"]

# For SecuLite v2, we will primarily rely on the main `nginx` service defined in
# `docker-compose.yml` (Section 3.7) to serve these assets. That Nginx service will
# typically copy assets from the `builder` stage of this Dockerfile or mount a volume
# that is populated by running the build stage of this Dockerfile.
# The key output of this Dockerfile is the `/app/frontend/dist` directory in the `builder` stage. 