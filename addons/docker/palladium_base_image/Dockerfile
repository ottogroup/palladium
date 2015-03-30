############################################################
# Dockerfile to build base image for palladium
# Based on continuumio/miniconda
############################################################

# Set the base image to  miniconda latest
FROM continuumio/miniconda3

# File Author / Maintainer
MAINTAINER Palladium 

# copy palladium 
ADD palladium.tar.gz /root/palladium

RUN   conda config --add channels https://conda.binstar.org/asmeurer \
      && conda config --add channels https://conda.binstar.org/menpo \
      && conda config --set ssl_verify false   # please deactivate if not needed

RUN conda install --yes --file /root/palladium/requirements.txt
   
# Install palladium
RUN cd root/palladium && python setup.py install
