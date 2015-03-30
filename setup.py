import os
from setuptools import setup, find_packages

version = '0.9'

install_requires = [
    'docopt',
    'flask',
    'joblib',
    'pandas',
    'scikit-learn',
    'ujson',
    ]

tests_require = [
    'pytest',
    'pytest-cov',
    ]

docs_require = [
    'julia',
    'rpy2',
    'Sphinx',
    'sphinx_rtd_theme',
    ]

here = os.path.abspath(os.path.dirname(__file__))
try:
    README = open(os.path.join(here, 'README.rst')).read()
    CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()
except IOError:
    README = CHANGES = ''


setup(name='palladium',
      version=version,
      description='',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      extras_require={
          'testing': tests_require,
          'docs': docs_require,
          'julia': ['julia'],
          'R': ['rpy2'],
          },
      entry_points={
          'console_scripts': [
              'pld-devserver = palladium.server:devserver_cmd',
              'pld-fit = palladium.fit:fit_cmd',
              'pld-grid-search = palladium.fit:grid_search_cmd',
              'pld-list = palladium.eval:list_cmd',
              'pld-test = palladium.eval:test_cmd',
              'pld-version = palladium.util:version_cmd',
              ],
          'pytest11': [
              'palladium = palladium.tests',
              ],
          },
      )
