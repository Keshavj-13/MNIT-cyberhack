FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --prefer-offline
COPY . .
# build each surface separately into dist/{surface}/
RUN npx vite build --config surfaces/customer/vite.config.ts  --outDir ../../dist/customer  --emptyOutDir
RUN npx vite build --config surfaces/admin/vite.config.ts     --outDir ../../dist/admin     --emptyOutDir
RUN npx vite build --config surfaces/attacker/vite.config.ts  --outDir ../../dist/attacker  --emptyOutDir
RUN npx vite build --config surfaces/showcase/vite.config.ts  --outDir ../../dist/showcase  --emptyOutDir


FROM node:20-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/dist ./dist
# serve all 4 surfaces simultaneously on their respective ports
CMD sh -c "serve -s dist/customer -l 3001 & serve -s dist/admin -l 3002 & serve -s dist/attacker -l 3003 & serve -s dist/showcase -l 3004 & wait"
