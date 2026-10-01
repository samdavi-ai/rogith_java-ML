FROM nginx:1.27-alpine
COPY index.html styles.css app.js camera-controller.js api-config.js /usr/share/nginx/html/
COPY deployment/nginx.conf /etc/nginx/conf.d/default.conf
