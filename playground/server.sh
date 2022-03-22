#!/bin/sh

. $(dirname -- "$0")/env.sh

exec $PYTHON -m hatter server \
    --conf server.yaml \
    "$@"
