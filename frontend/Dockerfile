FROM node:22-slim AS build

WORKDIR /app

ARG VITE_API_URL
ARG VITE_PUBLIC_MODE=false
ARG VITE_PATTERNS_ENABLED=false
ENV VITE_API_URL=${VITE_API_URL} VITE_PUBLIC_MODE=${VITE_PUBLIC_MODE} VITE_PATTERNS_ENABLED=${VITE_PATTERNS_ENABLED}

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
LABEL org.brasil-em-rede.frontend-runtime-config="v1"
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.d/40-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
