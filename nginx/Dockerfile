# nginx/Dockerfile

# Stage 1: Build the Vue.js application
FROM node:18-alpine AS builder

# Set the working directory in the container for the frontend app
WORKDIR /app/frontend

# Copy package.json and lock files first for caching
COPY ./frontend/package.json ./frontend/yarn.lock* ./frontend/package-lock.json* ./

# Install dependencies using npm ci for reproducible builds
RUN npm ci

# Copy the rest of the frontend application code
COPY ./frontend .

# Build the Vue.js application for production
# The output should typically be in the 'dist' directory
RUN npm run build

# Stage 2: Serve the built assets with Nginx
FROM nginx:1.25-alpine

# Remove default nginx website
RUN rm -rf /usr/share/nginx/html/*

# Copy the built static assets from the 'builder' stage's 'dist' directory
COPY --from=builder /app/frontend/dist /usr/share/nginx/html

# Copy the custom Nginx configuration file
# Assumes nginx.conf is in the same directory as this Dockerfile (./nginx/nginx.conf)
COPY ./nginx/nginx.conf /etc/nginx/nginx.conf

# Expose port 80 for Nginx
EXPOSE 80

# Default command to start Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"] 