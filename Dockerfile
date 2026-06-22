FROM caddy:2-alpine
COPY benchmark/ /srv/
COPY Caddyfile /etc/caddy/Caddyfile
