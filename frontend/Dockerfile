FROM node:20-alpine AS base

WORKDIR /app

COPY package.json .npmrc ./
RUN npm install

FROM base AS development

ENV VITE_API_BASE_URL=
ENV VITE_API_PROXY_TARGET=

COPY . .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]

FROM base AS builder

ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY . .

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
