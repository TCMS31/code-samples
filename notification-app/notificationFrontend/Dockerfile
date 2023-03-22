# syntax=docker/dockerfile:1

# ---- build the static bundle ----
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

# Baked in at build time: CRA inlines REACT_APP_* into the bundle.
ARG REACT_APP_API_URL=http://localhost:8613/
ENV REACT_APP_API_URL=$REACT_APP_API_URL

COPY . .
RUN npm run build


# ---- serve it ----
FROM nginx:1.27-alpine AS runtime

# Client-side routing: /logs must fall back to index.html.
RUN printf 'server {\n\
  listen 8080;\n\
  root /usr/share/nginx/html;\n\
  index index.html;\n\
  location / { try_files $uri $uri/ /index.html; }\n\
}\n' > /etc/nginx/conf.d/default.conf \
    && rm -f /etc/nginx/conf.d/default.conf.bak

COPY --from=builder /app/build /usr/share/nginx/html

# nginx:alpine ships an unprivileged "nginx" user; port 8080 needs no root.
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/run \
    && touch /var/run/nginx.pid && chown nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
