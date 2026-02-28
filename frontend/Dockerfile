# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Accept build-time env vars from Render
ARG VITE_API_URL
ARG VITE_WS_HOST

# Make them available to Vite during build
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_HOST=$VITE_WS_HOST

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build


# ── Stage 2: Serve with Nginx ─────────────────────────────────────────────────
FROM nginx:alpine

# Remove default nginx page
RUN rm -rf /usr/share/nginx/html/*

# Copy Vite build output
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config that handles SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]