# syntax=docker/dockerfile:1
FROM node:22-alpine AS base
WORKDIR /app

FROM base AS dependencies
COPY package.json ./
RUN npm install

FROM dependencies AS development
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM base AS production
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN npm run build
USER node
EXPOSE 3000
CMD ["npm", "start"]
