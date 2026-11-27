#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

if [[ "$EUID" -ne 0 ]]; then
    fail "Run with sudo, for example: sudo DEPLOY_DOMAIN=api.example.com bash deploy/ubuntu.sh"
fi

if [[ ! -r /etc/os-release ]]; then
    fail "Cannot identify the operating system."
fi
# shellcheck disable=SC1091
source /etc/os-release
[[ "${ID:-}" == "ubuntu" ]] || fail "This script supports Ubuntu only."

PROJECT_DIR="${PROJECT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
PROJECT_DIR="$(realpath "$PROJECT_DIR")"
[[ -f "$PROJECT_DIR/manage.py" && -f "$PROJECT_DIR/requirements.txt" ]] \
    || fail "PROJECT_DIR must point to the Django project root."
case "$PROJECT_DIR" in
    *[[:space:]]*) fail "PROJECT_DIR cannot contain whitespace." ;;
esac

APP_USER="${DEPLOY_USER:-${SUDO_USER:-}}"
[[ -n "$APP_USER" && "$APP_USER" != "root" ]] \
    || fail "Set DEPLOY_USER to a non-root Linux user with access to the project."
id "$APP_USER" >/dev/null 2>&1 || fail "Linux user '$APP_USER' does not exist."
runuser -u "$APP_USER" -- test -w "$PROJECT_DIR" \
    || fail "Linux user '$APP_USER' must be able to write to $PROJECT_DIR (SQLite database)."

DOMAIN="${DEPLOY_DOMAIN:-}"
if [[ -z "$DOMAIN" ]]; then
    if [[ -t 0 ]]; then
        read -r -p "Public domain name or IPv4 address: " DOMAIN
    else
        fail "Set DEPLOY_DOMAIN to a public domain name or IPv4 address."
    fi
fi
[[ "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ ]] \
    || fail "DEPLOY_DOMAIN must contain only letters, numbers, dots, and hyphens."

SERVICE_NAME="ecom-backend"
VENV="$PROJECT_DIR/.venv"
ENV_FILE="$PROJECT_DIR/.env.production"
WEB_ROOT="/var/www/$SERVICE_NAME"
NGINX_AVAILABLE="/etc/nginx/sites-available/$SERVICE_NAME"
NGINX_ENABLED="/etc/nginx/sites-enabled/$SERVICE_NAME"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
    build-essential \
    libjpeg-dev \
    nginx \
    python3 \
    python3-dev \
    python3-venv \
    redis-server \
    zlib1g-dev

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
    fail "Django 6.1 needs Python 3.12 or newer; use a compatible Ubuntu image."
fi

if [[ ! -x "$VENV/bin/python" ]]; then
    runuser -u "$APP_USER" -- python3 -m venv "$VENV"
fi
runuser -u "$APP_USER" -- "$VENV/bin/python" -m pip install --upgrade pip
runuser -u "$APP_USER" -- "$VENV/bin/python" -m pip install \
    -r "$PROJECT_DIR/requirements.txt"

if [[ ! -e "$ENV_FILE" ]]; then
    DJANGO_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"
    install -o "$APP_USER" -g "$APP_USER" -m 600 /dev/null "$ENV_FILE"
    cat >"$ENV_FILE" <<EOF
DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=$DOMAIN,localhost,127.0.0.1
DJANGO_STATIC_ROOT=$WEB_ROOT/static
DJANGO_MEDIA_ROOT=$WEB_ROOT/media
REDIS_CACHE_URL=redis://127.0.0.1:6379/1
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
GOOGLE_CLIENT_ID=
GITHUB_CLIENT_ID=
FACEBOOK_CLIENT_ID=
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
BREVO_API_KEY=
BREVO_SENDER_EMAIL=
BREVO_SENDER_NAME=
INSTAGRAM_ACCESS_TOKEN=
INSTAGRAM_ACCOUNT_ID=
INSTAGRAM_GRAPH_API_VERSION=v27.0
EOF
    chown "$APP_USER:$APP_USER" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
else
    chown "$APP_USER:$APP_USER" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    grep -q '^DJANGO_SECRET_KEY=.' "$ENV_FILE" \
        || fail "$ENV_FILE exists but DJANGO_SECRET_KEY is empty."
    grep -Fq "DJANGO_ALLOWED_HOSTS=$DOMAIN" "$ENV_FILE" \
        || fail "Update DJANGO_ALLOWED_HOSTS in $ENV_FILE to include $DOMAIN, then rerun."
    printf 'Preserving existing settings in %s\n' "$ENV_FILE"
fi

install -d -o "$APP_USER" -g www-data -m 2775 \
    "$WEB_ROOT/static" "$WEB_ROOT/media"
chgrp -R www-data "$WEB_ROOT/static" "$WEB_ROOT/media"
chmod -R g+rX "$WEB_ROOT/static" "$WEB_ROOT/media"

runuser -u "$APP_USER" -- env "DJANGO_ENV_FILE=$ENV_FILE" \
    "$VENV/bin/python" "$PROJECT_DIR/manage.py" check
runuser -u "$APP_USER" -- env "DJANGO_ENV_FILE=$ENV_FILE" \
    "$VENV/bin/python" "$PROJECT_DIR/manage.py" migrate --noinput
runuser -u "$APP_USER" -- env "DJANGO_ENV_FILE=$ENV_FILE" \
    "$VENV/bin/python" "$PROJECT_DIR/manage.py" collectstatic --noinput

systemctl enable --now redis-server

cat >"/etc/systemd/system/$SERVICE_NAME.service" <<EOF
[Unit]
Description=Gunicorn service for $SERVICE_NAME
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=$APP_USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=DJANGO_ENV_FILE=$ENV_FILE
UMask=0007
ExecStart=$VENV/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 --access-logfile - --error-logfile - core.wsgi:application
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat >"/etc/systemd/system/$SERVICE_NAME-celery.service" <<EOF
[Unit]
Description=Celery worker for $SERVICE_NAME
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=$APP_USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=DJANGO_ENV_FILE=$ENV_FILE
UMask=0007
ExecStart=$VENV/bin/celery -A core worker --loglevel=INFO --concurrency=1
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat >"$NGINX_AVAILABLE" <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    client_max_body_size 20M;

    location /static/ {
        alias $WEB_ROOT/static/;
    }

    location /media/ {
        alias $WEB_ROOT/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sfn "$NGINX_AVAILABLE" "$NGINX_ENABLED"
nginx -t
systemctl daemon-reload
systemctl enable "$SERVICE_NAME.service" "$SERVICE_NAME-celery.service"
for service in "$SERVICE_NAME.service" "$SERVICE_NAME-celery.service"; do
    if systemctl is-active --quiet "$service"; then
        systemctl restart "$service"
    else
        systemctl start "$service"
    fi
done
systemctl enable --now nginx
systemctl reload nginx

printf '\nDeployment complete: http://%s/\n' "$DOMAIN"
printf 'Edit %s to add integration credentials, then restart the services.\n' "$ENV_FILE"
printf 'Open TCP port 80 in the VM/cloud firewall. Configure HTTPS before production use.\n'
