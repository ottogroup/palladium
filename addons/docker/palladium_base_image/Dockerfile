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
    && conda update --yes conda

RUN wget --no-check-certificate https://raw.githubusercontent.com/ottogroup/palladium/1.0/requirements.txt

RUN conda install --yes --file requirements.txt

RUN conda install --no-deps palladium==1.0
