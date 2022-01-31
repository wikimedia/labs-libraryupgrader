#!/bin/sh
poetry export -f requirements.txt --output requirements.txt --without-hashes
poetry export -f requirements.txt --output requirements-dev.txt --dev --without-hashes
(cd runner && poetry export -f requirements.txt --output requirements.txt --without-hashes)
(cd runner && poetry export -f requirements.txt --output requirements-dev.txt --dev --without-hashes)
