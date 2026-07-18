# Stage 1: Build static assets
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx (non-root)
FROM nginx:alpine
RUN adduser -D -u 10001 -g '' appuser && \
    chown -R appuser:appuser /usr/share/nginx/html /var/cache/nginx /var/run /etc/nginx/conf.d
COPY --from=builder --chown=appuser:appuser /app/dist /usr/share/nginx/html
USER appuser
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
