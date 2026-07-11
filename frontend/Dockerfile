FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund

COPY . .

EXPOSE 3000

CMD ["npx", "next", "dev", "-H", "0.0.0.0", "-p", "3000"]
