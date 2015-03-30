.. _julia:

=============
Julia support
=============

.. contents::
   :local:


Palladium has support for using :class:`~palladium.interfaces.Model` objects that
are implemented in the Julia programming language.

To use Palladium's Julia support, you'll have to install Julia 0.3 or better
and the `julia Python package <https://pypi.python.org/pypi/julia>`_.
You'll also need to install the PyCall library in Julia::

  $ julia -e 'Pkg.add("PyCall"); Pkg.update()'

The following example also relies on the SVM Julia package.  This is
how you can install it::

  $ julia -e 'Pkg.add("StatsBase"); Pkg.add("SVM"); Pkg.update()'

.. warning:: 

  The latest PyCall version from GitHub is known to have `significant
  performance issues
  <https://github.com/stevengj/PyCall.jl/issues/113>`_.  It is
  recommended that you install revision 120fb03 instead.  To do this
  on Linux, change into your ``~/.julia/v0.3/PyCall`` directory and
  issue the necessary ``git checkout`` command::

    cd ~/.julia/v0.3/PyCall
    git checkout 120fb03

Let's now take a look at the example on how to use a model written in
Julia in the ``examples/julia`` folder in the source tree of Palladium
(:download:`config.py <../../examples/julia/config.py>`,
:download:`iris.data <../../examples/iris/iris.data>`).  The
configuration in that example defines the model to be of type
:class:`palladium.julia.ClassificationModel`:

.. code-block:: python

  'model': {
      '__factory__': 'palladium.julia.ClassificationModel',
      'fit_func': 'SVM.svm',
      'predict_func': 'SVM.predict',
      }

There's two required arguments to
:class:`~palladium.julia.ClassificationModel` and they're the dotted path to
the Julia function used for fitting, and the equivalent for the Julia
function that does the prediction.  The complete description of
available parameters is defined in the API docs:

.. automodule:: palladium.julia

  .. autoclass:: AbstractModel
    :members: __init__
