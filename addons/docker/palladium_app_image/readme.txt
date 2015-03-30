This script creates a Dockerfile and a copy of your application into
the folder. Then it is building the docker palladium image with your
application inside.

Run "create" command with the path to your application folder and the
image name as parameters:

    create.sh <path to folder> <owner/palladium_app_name:version> <owner/palladium_base_name:version>

Application folder structure:
.
|--- config.py
|--- setup.py (optional)
|--- requirements.txt (optional)
'--- python_packages (optional)
     |--- package1.tar.gz
     |--- package2.tar.gz
     '--- ...

If additional python packages must be installed, make sure a
requirements.txt is in your app folder. If conda does not support some
packages, create a folder "python_packages" in your application's
folder and put the package source code there. At the moment only
.tar.gz are supported.

If you want to add conda channels you, have to do it manually in the
create.sh script. Edit create.sh and go to the line where the conda
channels are mentioned. You can enter your channels there by following
the example. If you run the script now, your channels
should be added to the image during the build process.

TEST:

1. Create app image
2. run app_predict image with   
   sudo docker run -d app_name_predict

3. get container ID   
   sudo docker run ps

4. get container IP address
   sudo docker inspect -f '{{.NetworkSettings.IPAddress}}' container_id

5. test predict request
   http://container_ip:8000/predict...

or:

2. run app_predict image with
   sudo docker run -d -p <port_number>:8000 app_name_predict

3. test predict request
   http://localhost:port_number/predict...
