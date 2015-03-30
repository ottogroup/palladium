============
 Deployment
============

In this section, you will find information on how to run
Palladium-based application with another web server instead of Flask's
built in solution, and how to benchmark your service. Additionally,
you will find information on how to use provided scripts to
automatically generate Docker images of your service and how to deploy
such Docker images using Mesos / Marathon.

.. _web-server-installation:

Web server installation
=======================

Palladium uses HTTP to respond to prediction requests.  Through use of the
*WSGI protocol* (via Flask), Palladium can be used together with a `variety
of web servers <http://wsgi.readthedocs.org/en/latest/servers.html>`_.

For convenience, a web server is included for development purposes.
To start the built-in web server, use the :ref:`pld-devserver
<pld-devserver>` command.

For production use, you probably want to use something faster and more
robust.  Many options are listed in the `Flask deployment docs
<http://flask.pocoo.org/docs/deploying/>`_.  If you follow any of
these instructions, be aware that the Flask app in Palladium is available as
``palladium.server:app``.  So here's how you would start an Palladium prediction
server using `gunicorn <http://gunicorn.org/>`_:

.. code-block:: bash

   export PALLADIUM_CONFIG=/path/to/myconfig.py
   gunicorn palladium.server:app

An example configuration to `use nginx to proxy requests to gunicorn
<http://flask.pocoo.org/docs/0.10/deploying/wsgi-standalone/#proxy-setups>`_
is also available. It can be used without modification for our example
and has to be made available in the `/etc/nginx/sites-enabled/`
folder and is active after a restart of `nginx`. For convenience it is
reprinted here:

.. code-block:: text

  server {
      listen 80;

      server_name _;

      access_log  /var/log/nginx/access.log;
      error_log  /var/log/nginx/error.log;

      location / {
	  proxy_pass         http://127.0.0.1:8000/;
	  proxy_redirect     off;

	  proxy_set_header   Host             $host;
	  proxy_set_header   X-Real-IP        $remote_addr;
	  proxy_set_header   X-Forwarded-For  $proxy_add_x_forwarded_for;
      }
  }

Benchmarking the service with Apache Benchmark
----------------------------------------------

In order to benchmark the response time of a service, existing tools
like `Apache Benchmark (ab)
<http://httpd.apache.org/docs/2.4/en/programs/ab.html>`_ or `siege
<http://www.joedog.org/siege-home/>`_ can be used. They can be
installed using install packages, e.g., for Ubuntu with `apt-get
install apache2-utils` and `sudo apt-get install siege`.

If a web server with the Iris predict service is running (either using
the built-in :ref:`pld-devserver <pld-devserver>` or a faster solution
as described in :ref:`web-server-installation`), the `ab` benchmarking
can be run as follows:

.. code-block:: bash

  ab -n 1000 -c 10 "http://localhost:5000/predict?
                    sepal%20length=5.2&sepal%20width=3.5&
                    petal%20length=1.5&petal%20width=0.2"

In this `ab` call, it is assumed that the web server is available at
port 5000 of localhost and 1000 requests with 10 concurrent requests
at a time are sent to the web server. The output provides a number of
statistics about response times of the calls performed.

.. note::

  If there is an error in the sample request used, response times
  might be suspiciously low. If very low response times occur, it
  might be worth manually checking the corresponding response of used
  request URL.

.. note::

  `ab` does not allow to use different URLs in a benchmark run. If
  different URLs are important for benchmarking, either `siege
  <http://www.joedog.org/siege-home/>`_ or a `multiple URL patch
  <https://github.com/philipgloyne/apachebench-for-multi-url>`_ for ab
  could be used


Building a Docker image with your Palladium application
=======================================================

First you need to pull or build the palladium_base image. If you want
to build the base image, use the ``create_base.sh`` script and the
Dockerfile located in the directory
``addons/docker/palladium_base_image.`` Alternatively, you can
download the files here: :download:`create_base.sh
<../../addons/docker/palladium_base_image/create_base.sh>` and
:download:`Dockerfile
<../../addons/docker/palladium_base_image/Dockerfile>`.

Run in your terminal the build command:

.. code-block:: bash

  sudo create_base.sh <path_to_palladium> <owner/palladium_base_name:version> 

A docker image with the name ``owner/palladium_base:version`` should now be
created. You can check this with

.. code-block:: bash

  sudo docker images

If network problems occur while you are running the build script, a
possible solution may be to disable dnsmasq in your
NetworkManager.conf. You can do that by commenting out the line
dns=dnsmasq in /etc/NetworkManager/NetworkManager.conf

Afterwards restart your network manager and Docker.

.. code-block:: bash
  
  sudo restart network-manager
  sudo restart docker

Now you can build your application on top of the Palladium base
image. You can download the script here: :download:`create.sh
<../../addons/docker/palladium_app_image/create.sh>`. Alternatively,
you can also find it in the source folder
``addons/docker/palladium_app_image``. Run the script with the
command:

.. code-block:: bash

  create.sh <path_to_app_folder> <owner/palladium_app_name:version>
            <owner/palladium_base_name:version>
      
For more information take a look at the :download:`readme.txt
<../../addons/docker/palladium_app_image/readme.txt>` file.

Type in the following command to test your image:

.. code-block:: bash

  sudo docker run -i -t <owner/palladium_app_name:version> /bin/bash

Setup Palladium with Mesos / Marathon and Docker
================================================

This section describes how to setup Mesos / Marathon with a
containerized Palladium application. If you have not built a docker image
with your Palladium application yet, you can follow the instructions that
are provided in the `Building a docker image with your Palladium
application`_ section.

For the installation of Mesos and Marathon you can follow the `guide
on Mesosphere. <http://mesosphere.com/docs/getting-started>`_ If you
want to try it out locally first, we recommend to `set up a single
node Mesosphere
cluster. <http://mesosphere.com/docs/getting-started/developer/single-node-install>`_
Before adding a new application to Marathon you need to make sure that
the Mesos slaves and Marathon are configured properly to work with
Docker. To do so, follow the steps as described in the `Marathon
documentation.
<https://mesosphere.github.io/marathon/docs/native-docker.html>`_

An easy way to add a new application to Marathon is to use its REST
API. For this task you need a json file which contains the relevant
information for Marathon. A basic example of the json file could look
like this:

.. code-block:: json

  {
      "id": "<app_name>",
      "container": {
          "docker": {
              "image": "<owner/palladium_app_name:version>",
	      "network": "BRIDGE",
	      "parameters": [
		  {"key": "link", "value":"<some_container_to_link>"}
	      ],
	      "portMappings": [
		  { "containerPort": 8000, "hostPort": 0, "servicePort": 9000,
                    "protocol": "tcp" }
	      ]
          },
          "type": "DOCKER",
          "volumes": [
	      {
		  "containerPath": "/path/in/your/container",
		  "hostPath": "/host/path",
		  "mode": "RO"
	      }
	  ]
      },
      "cpus": 0.2,
      "mem": 256.0,
      "instances": 3,
      "healthChecks": [
	  {
	      "protocol": "HTTP",
	      "portIndex": 0,
	      "path": "/alive",
	      "gracePeriodSeconds": 5,
	      "intervalSeconds": 20,
	      "maxConsecutiveFailures": 3
	  }
      ],
      "upgradeStrategy": {
          "minimumHealthCapacity": 0.5
      }
  }

You have to replace the Docker image name, port number (currently set
to 8000) and - if there is any dependency - specify links to other
containers. If you have a Docker image of the Iris service available
(named `user/palladium-iris_predict:0.1`), you can use this file:

.. code-block:: json

  {
    "id": "palladium-iris", 
      "container": {
	  "docker": {
	      "image": "user/palladium-iris_predict:0.1",
	      "network": "BRIDGE",
	      "parameters": [
	      ],
	      "portMappings": [
		  { "containerPort": 8000, "hostPort": 0, "servicePort": 9000,
                    "protocol": "tcp" }
	      ]
	  },
	  "type": "DOCKER",
	  "volumes": [
	   ]
      },
      "cpus": 0.2,
      "mem": 256.0,
      "instances": 3,
      "healthChecks": [
	  {
	      "protocol": "HTTP",
	      "portIndex": 0,
	      "path": "/alive",
	      "gracePeriodSeconds": 5,
	      "intervalSeconds": 20,
	      "maxConsecutiveFailures": 3
	  }
      ],
      "upgradeStrategy": {
	  "minimumHealthCapacity": 0.5
      }
  }

Now you can send the json application file to Marathon via POST
(assuming Marathon is available at `localhost:8080`:

.. code-block:: bash

    curl -X POST -H "Content-Type: application/json" localhost:8080/v2/apps
         -d @<path-to-json-file>

You can see the status of your Palladium service instances using the
Marathon web user interface (available at `http://localhost:8080` if
you run the single node installation mentioned above) and can scale
the number of instances as desired. Marathon keeps track of the Palladium
instances. If a service instance breaks down, a new one will be
started automatically.


Authorization
=============

Sometimes you will want the Palladium web service's entry points */predict*
and */alive* to be secured by OAuth2 or similar.  Defining
``predict_decorators`` and ``alive_decorators`` in the Palladium
configuration file allows you to put any decorators in place to check
authentication.

Let us first consider an example where you want to use *HTTP Basic
Auth* to guard the entry points.  Consider this code taken from the
`Flask snippets <http://flask.pocoo.org/snippets/8/>`_ repository:

.. code-block:: python

  # file: mybasicauth.py

  from functools import wraps
  from flask import request, Response


  def check_auth(username, password):
      """This function is called to check if a username /
      password combination is valid.
      """
      return username == 'admin' and password == 'secret'

  def authenticate():
      """Sends a 401 response that enables basic auth"""
      return Response(
      'Could not verify your access level for that URL.\n'
      'You have to login with proper credentials', 401,
      {'WWW-Authenticate': 'Basic realm="Login Required"'})

  def requires_auth(f):
      @wraps(f)
      def decorated(*args, **kwargs):
          auth = request.authorization
          if not auth or not check_auth(auth.username, auth.password):
              return authenticate()
          return f(*args, **kwargs)
      return decorated

The ``requires_auth`` can now be used to decorate Flask views to guard
them with basic authentication.  Palladium allows us to add decorators to
the */predict* and */alive* views that it defines itself.  To do this,
we only need to add this bit to the Palladium configuration file:

.. code-block:: python

  'predict_decorators': [
      'mybasicauth.requires_auth',
      ],

  'alive_decorators': [
      'mybasicauth.requires_auth',
      ],

Of course, alternatively, you could set up your mod_wsgi server to
take care of authentication.

Using `Flask-OAuthlib <http://flask-oauthlib.readthedocs.org>`_ to
guard the two views using OAuth2 follows the same pattern.  We will
configure and use the :class:`flask_oauthlib.provider.OAuth2Provider
<http://flask-oauthlib.readthedocs.org/en/latest/api.html#oauth2-provider>`
for security.  In our own package, we might have an instance of
:class:`~flask_oauthlib.provider.OAuth2Provider` and a
``require_oauth`` decorator defined thus:

.. code-block:: python

  # file: myoauth.py

  from flask_oauthlib.provider import OAuth2Provider
  from palladium.server import app


  oauth = OAuth2Provider(app)

  # more setup code here... see Flask-OAuthlib

  require_oauth = oauth.require_oauth('myrealm')

Alternatively, to get more decoupling from Palladium's Flask ``app``, you
can use the following snippet inside your Palladium configuration and
assign the Flask app to
:class:`~flask_oauthlib.provider.OAuth2Provider` at application
startup:

.. code-block:: python

  'oauth_init_app': {
      '__factory__': 'myoauth.oauth.init_app',
      'app': 'palladium.server.app',
      },

Now, to guard, */predict* and */alive* with the previously defined
``require_oauth``, add this to your configuration:

.. code-block:: python

  'predict_decorators': [
      'myoauth.require_oauth'
      ],

  'alive_decorators': [
      'myoauth.require_oauth'
      ],
