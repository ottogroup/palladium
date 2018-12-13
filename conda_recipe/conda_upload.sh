#!/usr/bin/env bash

# Compare with https://gist.github.com/zshaheen/fe76d1507839ed6fbfbccef6b9c13ed9

set -ev

# Only need to change these two variables
PKG_NAME=palladium
USER=ottogroup

OS=$TRAVIS_OS_NAME-64
mkdir ~/conda-bld

conda install conda-build
conda install anaconda-client

conda config --add channels conda-forge  # for requests-mock
conda config --set anaconda_upload no
export CONDA_BLD_PATH=~/conda-bld
conda build .
FILENAME=`ls -t $CONDA_BLD_PATH/$OS/$PKG_NAME* | head -1`
anaconda -t $CONDA_UPLOAD_TOKEN upload -u $USER $FILENAME
