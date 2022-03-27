#!/bin/sh

. $(dirname -- "$0")/env.sh

exec $PYTHON -m boxhatter server \
    --conf $RUN_PATH/server.yaml \
    --db $DATA_PATH/boxhatter.db \
    "$@"
