FROM node:24.19.0-bookworm-slim@sha256:3638d9a6fe4030bd716be989438248074489337ba3275657f93595428be4fc03 AS node_runtime

FROM mcr.microsoft.com/playwright:v1.62.1-noble@sha256:dcc5531e97840b9b5e794f2814476b21571c5124a3fca2267d73041f56e7580e

COPY --from=node_runtime /usr/local/ /usr/local/

ENV NEXT_TELEMETRY_DISABLED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /workspace

COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/package.json
COPY apps/e2e/package.json ./apps/e2e/package.json
COPY packages/api-client/package.json ./packages/api-client/package.json
COPY packages/test-data/package.json ./packages/test-data/package.json

RUN --mount=type=cache,target=/root/.npm npm ci

CMD ["sleep", "infinity"]
