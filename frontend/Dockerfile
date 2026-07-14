FROM node:22-slim AS base

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund

COPY . .

EXPOSE 3000

FROM base AS development
CMD ["npx", "next", "dev", "-H", "0.0.0.0", "-p", "3000"]

FROM base AS build
ARG NEXT_PUBLIC_API_URL=/api
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN npm run build

FROM build AS production
ENV NODE_ENV=production
CMD ["npm", "run", "start", "--", "--host", "0.0.0.0", "--port", "3000"]
