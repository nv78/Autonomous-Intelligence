FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install --force \
    && npm cache clean --force 

COPY . .

EXPOSE 3000

CMD ["npm", "run", "start"]
