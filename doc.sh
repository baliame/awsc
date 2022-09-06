#!/usr/bin/env bash

rm -rf src/generated
if ! which sphinx-autodoc >/dev/null 2>&1; then
	git clone https://github.com/elcorto/sphinx-autodoc
	pip install -e ./sphinx-autodoc
	#rm -rf sphinx-autodoc
fi
sphinx-autodoc -d doc -s src -i awsc
make html
exit 0
