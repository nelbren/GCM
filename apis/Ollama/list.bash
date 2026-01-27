#!/bin/bash
mydir=$(dirname "$0")
source ${mydir}/secret.bash
../../.venv/bin/python query_model.py list
