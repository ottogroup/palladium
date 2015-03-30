#!/bin/bash
############################################
# Script to build a palladium_base docker image
#
############################################

# $1 = path to palladium
# $2 = base image name, i.e., palladium_user/palladium_base:0.1

# Copy files into same directory as Dockerfile 
tar cvzf palladium.tar.gz --exclude .git --directory=$1 .

# Build docker image
sudo docker build -t $2 .

# Remove tar file
rm palladium.tar.gz
