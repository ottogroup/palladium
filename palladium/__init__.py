import pkg_resources  # pragma: no cover

try:
    __version__ = pkg_resources.get_distribution("palladium").version  # pragma: no cover
except:
    __version__ = 'n/a'
