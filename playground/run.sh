#!/bin/bash

PYTHONPATH="../src_py" python -m hatter.main -c conf.yaml --web-path ../build/jshatter $*
