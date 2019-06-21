#!/usr/bin/env bash

# BOKEH SERVER

ROOT_DIR=$(dirname "${BASH_SOURCE}")

source ${ROOT_DIR}/${ENV_NAME:-.env}

export FLASK_ENV=${FLASK_ENV:-production}
PORT_BOKEH=${PORT_BOKEH:-5101}

${PY_HOME}/bin/bokeh serve --port ${PORT_BOKEH} \
 --allow-websocket-origin=${URL} \
 --allow-websocket-origin=${ADDRESS}:${PORT_BOKEH} \
 --allow-websocket-origin=${ADDRESS}:${PORT_APP} \
 --address ${ADDRESS} \
 --show ${ROOT_DIR}/bk_server
