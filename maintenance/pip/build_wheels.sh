#!/bin/bash

set -e

rm -rf wheels_temp wheels

mkdir wheels_temp
mv pyproject.toml pyproject.toml.orig
cp maintenance/pip/pyproject-build-pip.toml pyproject.toml
for x in /opt/python/* ; do
    "$x/bin/python" -c 'import sys ; sys.exit(not ((3, 6, 0) <= sys.version_info < (3, 11, 0)))' || continue
    #"$x/bin/python" -c 'import sys ; sys.exit(not (sys.version_info[:2] == (3, 7)))' || continue
    "$x/bin/pip" install --upgrade pip
    "$x/bin/pip" install --only-binary=:all: --no-cache-dir -r maintenance/pip/requirements-build-pip.txt
    "$x/bin/pip" wheel -v . -w wheels_temp
done

mkdir wheels
for wheel in wheels_temp/pyrocko-*.whl ; do
    auditwheel repair "$wheel" --plat $PLAT -w wheels
    rm "$wheel"
done

mv pyproject.toml.orig pyproject.toml
