"""Module to be used for exposing the web service with other WSGI
servers. It initializes Palladium's configuration and provides the
Flask object.
"""
from .util import initialize_config
from .server import app

# Initialization is needed to obtain same behavior of pld-devserver
# and other WSGI servers (e.g., gunicorn). Without this initialization
# call, initialization would be delayed until the first request arrives
initialize_config()
