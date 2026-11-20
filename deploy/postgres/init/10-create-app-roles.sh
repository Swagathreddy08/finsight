#!/bin/sh
set -eu

: "${MIGRATOR_DB_PASSWORD:?MIGRATOR_DB_PASSWORD is required}"
: "${APP_DB_PASSWORD:?APP_DB_PASSWORD is required}"

psql \
  --set=ON_ERROR_STOP=1 \
  --set=migrator_password="$MIGRATOR_DB_PASSWORD" \
  --set=app_password="$APP_DB_PASSWORD" \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" <<'SQL'
CREATE ROLE finsight_migrator LOGIN BYPASSRLS PASSWORD :'migrator_password';
CREATE ROLE finsight_app LOGIN PASSWORD :'app_password';
GRANT ALL PRIVILEGES ON DATABASE finsight TO finsight_migrator;
GRANT CONNECT ON DATABASE finsight TO finsight_app;
GRANT ALL PRIVILEGES ON SCHEMA public TO finsight_migrator;
SQL
