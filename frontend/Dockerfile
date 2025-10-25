FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build -- --configuration production

FROM nginx:1.25-alpine
COPY --from=build /app/dist/smart-advisor /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
