# ====================================================================
# DermaSense AI - Frontend Container (React, Vite, Tailwind, Nginx)
# Smart India Hackathon 2025 (Team Healthnautix, PS 25049)
# ====================================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package descriptors
COPY package*.json ./
RUN npm install

# Copy source code and build production bundle
COPY . .
RUN npm run build

# Stage 2: Lean Nginx production server
FROM nginx:1.25-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

