#!/usr/bin/env bash

export LC_ALL=en_US.UTF-8
export LANG=en_US.utf-8

ROOT_DIR=$(dirname "${BASH_SOURCE}")

source ${ROOT_DIR}/${ENV_NAME:-.env}

export FLASK_ENV=${FLASK_ENV:-production}
export FLASK_APP=${ROOT_DIR}/app.py
export FLASK_RUN_PORT=${FLASK_RUN_PORT:-5100}

${PY_HOME}/bin/flask run
