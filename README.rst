.. image:: https://github.com/ottogroup/palladium/actions/workflows/build_test_python.yml/badge.svg
    :target: https://github.com/ottogroup/palladium/actions/workflows/build_test_python.yml
    :alt: Build status

.. image:: https://coveralls.io/repos/ottogroup/palladium/badge.svg?branch=master
    :target: https://coveralls.io/r/ottogroup/palladium
    :alt: Test coverage status

.. image:: https://readthedocs.org/projects/palladium/badge/?version=latest
    :target: https://palladium.readthedocs.io/en/latest/
    :alt: Documentation status

.. image:: https://img.shields.io/pypi/v/palladium.svg
    :target: https://pypi.python.org/pypi/palladium/
    :alt: Latest version

.. image:: https://img.shields.io/pypi/pyversions/palladium.svg
    :target: https://pypi.python.org/pypi/palladium/
    :alt: Supported Python versions

.. image:: https://img.shields.io/pypi/l/palladium.svg
    :target: https://pypi.python.org/pypi/palladium/
    :alt: License

Palladium
=========

Palladium provides means to easily set up predictive
analytics services as web services.  It is a **pluggable framework**
for developing real-world **machine learning solutions**.  It provides
generic implementations for things commonly needed in machine
learning, such as dataset loading, model training with parameter
search, a web service, and persistence capabilities, allowing you to
concentrate on the core task of developing an accurate machine
learning model.  Having a well-tested core framework that is used for
a number of different services can lead to a reduction of costs during
development and maintenance due to harmonization of different services
being based on the same code base and identical processes. Palladium
has a web service overhead of a few milliseconds only, making it
possible to **set up services with low response times**.

A **configuration file** lets you conveniently tie together existing
components with components that you developed.  As an example, if what
you want to do is to develop a model where you load a dataset from a
CSV file or an SQL database, and train an SVM classifier to predict
one of the rows in the data given the others, and then find out about
your model's accuracy, then that's what Palladium allows you to do
**without writing a single line of code**. However, it is also
possible to independently integrate own solutions.

.. image:: https://raw.githubusercontent.com/ottogroup/palladium/master/docs/palladium_illustration.png
   :width: 700px
   :align: center
   :alt: Illustration of Palladium

|

Much of Palladium's functionality is based on the **scikit-learn**
library.  Thus, a lot of times you will find yourself looking at the
`documentation for scikit-learn <http://scikit-learn.org/>`_ when
developing with Palladium.  Although being implemented in Python,
Palladium provides support for other languages and is shipped with
examples how to **integrate and expose R and Julia models**.

For an efficient deployment of services based on Palladium, a script to
**create Docker images automatically** is provided. In order to manage
and monitor a number of Palladium service instances in a cluster,
**Mesosphere’s Mesos framework Marathon can be used for deployment**,
also enabling **scalability by having a variable number of service
nodes behind a load balancer**.  Examples how to create Palladium
Docker images and how to use them with Mesos / Marathon are part of
the documentation. Other important aspects – especially relevant in
enterprise contexts for setting up productive services – like
**authentication, logging, or monitoring, can be easily integrated via
pluggable decorator lists** in the configuration file of a service,
keeping track of service calls and corresponding permissions.

Everyone is welcome to contribute to Palladium. More information on
how to to contribute can be found in the FAQ section of the
`Palladium documentation <http://palladium.readthedocs.org>`_.

Links
-----

- Source code repository at GitHub: https://github.com/ottogroup/palladium
- Documentation including installation instructions and tutorial: http://palladium.readthedocs.org
- Mailing list: https://groups.google.com/forum/#!forum/pld-list
- Maintainer: `Andreas Lattner <https://github.com/alattner>`_
