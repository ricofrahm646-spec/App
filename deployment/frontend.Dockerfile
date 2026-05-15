FROM node:20-alpine

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend /app/frontend
RUN npm run build

CMD ["npm", "run", "start"]
