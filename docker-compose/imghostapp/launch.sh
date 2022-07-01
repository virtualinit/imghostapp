#!/usr/bin/env bash

set -e
cd /workspace
export PYTHONPATH=/workspace:$PYTHONPATH

if [ -z "$SECRET_KEY" ]
then
    echo "SECRET_KEY is not set. Using default value."
    export SECRET_KEY="111ioii2!n7dv+p@kq905a1m7zs7%_5%j9zw@%8qw20z&*k+b_"
fi

if [ -z "$ADMIN_INITIAL_PASSWORD" ]
then
    echo "ADMIN_INITIAL_PASSWORD is not set. Using 'password'."
    export ADMIN_INITIAL_PASSWORD="password"
fi

if [ -z "$DATABASE_HOST" ]
then
    echo "DATABASE_HOST is not set. Using 'localhost' as default."
    export DATABASE_HOST="localhost"
fi

if [ -z "$POSTGRES_USER" ]
then
    echo "POSTGRES_USER is not set. Using 'postgres' as default value."
    export POSTGRES_USER="postgres"
fi

if [ -z "$POSTGRES_PASSWORD" ]
then
    echo "POSTGRES_PASSWORD is not set. Using 'postgres' as default value."
    export POSTGRES_PASSWORD="postgres"
fi

if [ -z "$POSTGRES_DB" ]
then
    echo "POSTGRES_DB is not set. Using 'imagestore' as default value."
    export POSTGRES_DB="imagestore"
fi

if [ -z "$GUNICORN_CMD_ARGS" ]
then
    echo "GUNICORN_CMD_ARGS is not set. Using default settings."
    export GUNICORN_CMD_ARGS="--workers 3 --bind 0.0.0.0:8080 --timeout 300"
fi

# set environment
make static
make migrate
python3 manage.py createuser

# launch application
gunicorn imagestore.wsgi:application
