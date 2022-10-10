#!/usr/bin/env bash

set -e

poetry run black --check discordbot
poetry run isort --profile black --check-only discordbot