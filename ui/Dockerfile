FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/dist ./dist
# all 4 surfaces served via run.py ports — single-page app, serve on 3000 mapped per surface
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
