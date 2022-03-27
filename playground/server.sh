#!/bin/sh

. $(dirname -- "$0")/env.sh

exec $PYTHON -m hatter server \
    --conf $RUN_PATH/server.yaml \
    --db $DATA_PATH/hatter.db \
    "$@"
