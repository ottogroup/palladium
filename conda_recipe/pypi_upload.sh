#!/usr/bin/env bash

set -ev

pip install twine
pip install wheel

rm -f dist/*
python setup.py sdist
python setup.py bdist_wheel
twine upload --skip-existing -u $PYPI_USERNAME -p $PYPI_PASSWORD dist/*
