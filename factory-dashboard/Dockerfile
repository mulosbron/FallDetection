# Build stage includes all devDependencies (react-scripts).
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY public ./public
COPY tsconfig.json ./
COPY src ./src

ARG REACT_APP_WEB_API_BASE=http://localhost:5000
ARG REACT_APP_SIGNALR_URL=http://localhost:5001/alertHub

ENV REACT_APP_WEB_API_BASE=$REACT_APP_WEB_API_BASE
ENV REACT_APP_SIGNALR_URL=$REACT_APP_SIGNALR_URL

RUN npm run build

# Static files
FROM nginx:1.27-alpine AS production

RUN apk add --no-cache curl

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:80/health >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
