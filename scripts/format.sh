#!/usr/bin/env bash
set -e

poetry run black discordbot
poetry run isort --profile black discordbot