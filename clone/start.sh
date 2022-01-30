#!/usr/bin/env bash
source ./env/bin/activate
export FLASK_ENV="development"
export FLASK_APP=index.py
flask run --host 0.0.0.0 --port 7000
