#!/usr/bin/env bash

mypy src --ignore-missing-imports --show-error-codes || exit 1
modify=1
autoflake -i -r src/awsc --exclude resources.py --exclude __init__.py --exclude main.py --check && isort src --profile black -c && black src --check && modify=0

autoflake -i -r src/awsc --exclude resources.py --exclude __init__.py --exclude main.py
black src
isort src --profile black
pylint src --fail-under 9 --fail-on E || exit 1
[ $modify -gt 0 ] && echo "Formatted repo, re-run commit" && exit 1

exit 0