import os
from setuptools import setup, find_packages

version = open('VERSION').read().rstrip()

install_requires = [
    'docopt',
    'flask',
    'joblib',
    'numpy',
    'pandas',
    'psutil',
    'requests',
    'scikit-learn',
    'sqlalchemy',
    'ujson',
    ]

tests_require = [
    'pytest',
    'pytest-cov',
    'requests-mock',
    ]

docs_require = [
    'julia',
    'rpy2',
    'Sphinx',
    'sphinx_rtd_theme',
    ]

here = os.path.abspath(os.path.dirname(__file__))
try:
    README = open(os.path.join(here, 'README.rst'), encoding='utf-8').read()
    CHANGES = open(os.path.join(here, 'CHANGES.txt'), encoding='utf-8').read()
except IOError:
    README = CHANGES = ''


setup(name='palladium',
      version=version,
      description='Framework for setting up predictive analytics services',
      long_description=README,
      url='https://github.com/ottogroup/palladium',
      author='Otto Group',
      author_email='palladium@ottogroup.com',
      license='Apache License, Version 2.0',
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
      ],
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
              'pld-admin = palladium.fit:admin_cmd',
              'pld-devserver = palladium.server:devserver_cmd',
              'pld-fit = palladium.fit:fit_cmd',
              'pld-grid-search = palladium.fit:grid_search_cmd',
              'pld-list = palladium.eval:list_cmd',
              'pld-stream = palladium.server:stream_cmd',
              'pld-test = palladium.eval:test_cmd',
              'pld-upgrade = palladium.util:upgrade_cmd',
              'pld-version = palladium.util:version_cmd',
              ],
          'pytest11': [
              'palladium = palladium.tests',
              ],
          },
      scripts=['bin/pld-dockerize'],
      )
