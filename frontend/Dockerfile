FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install --force \
    && npm cache clean --force 

COPY . ./app

EXPOSE 3000

<<<<<<< HEAD
CMD ["npm", "run", "start"]
=======
CMD ["npm", "run", "start"]
>>>>>>> main
