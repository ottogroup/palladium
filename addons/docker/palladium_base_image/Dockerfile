############################################################
# Dockerfile to build base image for palladium
# Based on continuumio/miniconda
############################################################

# Set the base image to  miniconda latest
FROM continuumio/miniconda3

# File Author / Maintainer
MAINTAINER Palladium 

RUN conda config --add channels https://conda.binstar.org/ottogroup \
    && conda config --set ssl_verify false \
    && conda update --yes conda \
    && wget --no-check-certificate https://raw.githubusercontent.com/ottogroup/palladium/1.1.0.1/requirements.txt \
    && conda install --yes --quiet --file requirements.txt \
    && conda install --yes --no-deps --quiet palladium==1.1.0.1 \
    && conda clean --yes --all
