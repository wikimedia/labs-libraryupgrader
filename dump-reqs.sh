#!/bin/sh
poetry export -f requirements.txt --output requirements.txt
poetry export -f requirements.txt --output requirements-dev.txt --dev
(cd runner && poetry export -f requirements.txt --output requirements.txt)
(cd runner && poetry export -f requirements.txt --output requirements-dev.txt --dev)
