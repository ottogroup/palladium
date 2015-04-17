import pkg_resources

try:
    __version__ = pkg_resources.get_distribution("palladium").version
except:
    __version__ = 'n/a'
