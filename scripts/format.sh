#!/usr/bin/env bash
set -e

poetry run black discordbot
poetry run isort discordbot