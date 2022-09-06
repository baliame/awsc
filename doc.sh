#!/usr/bin/env bash

rm -rf src/generated
if ! which sphinx-apidoc >/dev/null 2>&1; then
	git clone https://github.com/elcorto/sphinx-autodoc
	cd sphinx-autodoc
	python3 -m pip install -e .
	cd -
	rm -rf sphinx-autodoc
fi
sphinx-autodoc -d doc -s src -i awsc
make html
exit 0
