#!/usr/bin/env bash

# BOKEH SERVER

ROOT_DIR=$(dirname "${BASH_SOURCE}")

source ${ROOT_DIR}/${ENV_NAME:-.env}

export FLASK_ENV=${FLASK_ENV:-production}
PORT_BOKEH=${PORT_BOKEH:-5101}
ADDRESS=${ADDRESS:-127.0.0.1}

${PY_HOME}/bin/bokeh serve --port ${PORT_BOKEH} \
 --allow-websocket-origin=${HOST_URL} \
 --allow-websocket-origin=${ADDRESS}:${PORT_BOKEH} \
 --address 127.0.0.1 \
 --show ${ROOT_DIR}/bk_server
