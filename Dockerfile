FROM node:20-slim
WORKDIR /app
COPY package.json ./
RUN npm install
COPY bot.mjs ./
ENV NODE_ENV=production
CMD ["node", "bot.mjs"]
