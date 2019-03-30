#!/bin/bash

set -e

python3 setup.py sdist bdist_wheel
pip3 install --upgrade dist/tnetserver-1.0-py3-none-any.whl

exit 0
