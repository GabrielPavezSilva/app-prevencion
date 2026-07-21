# Stage 1: build del SPA con Vite
FROM node:20-alpine AS builder

WORKDIR /app

# ARGs inyectados desde docker-compose en tiempo de build
ARG VITE_API_URL=http://localhost:8000/api
ARG VITE_HARDWARE_URL=http://localhost:5050

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_HARDWARE_URL=$VITE_HARDWARE_URL

COPY package*.json ./
RUN npm ci --ignore-scripts

COPY . .
RUN npm run build

# Stage 2: servidor estático con Nginx
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# Config mínima para React Router (SPA fallback a index.html)
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
