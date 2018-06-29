"""Interfaces defining the behaviour of Palladium's components.
"""

from abc import abstractmethod
from abc import ABCMeta

from sklearn.base import BaseEstimator

from . import __version__
from .util import PluggableDecorator


def annotate(obj, metadata=None):
    base_metadata = getattr(obj, '__metadata__', {})
    if metadata is not None:
        base_metadata.update(metadata)
        obj.__metadata__ = base_metadata
    return obj.__metadata__


class DatasetLoaderMeta(ABCMeta):
    def __init__(cls, name, bases, attrs, **kwargs):
        super().__init__(name, bases, attrs, **kwargs)
        cls.__call__ = PluggableDecorator('load_data_decorators')(cls.__call__)


class DatasetLoader(metaclass=DatasetLoaderMeta):
    """A :class:`~palladium.interfaces.DatasetLoader` is responsible for
    loading datasets for use in training and evaluation.
    """

    @abstractmethod
    def __call__(self):
        """Loads the data and returns a tuple *(data, target)*, or
        *(X, y)*.

        :return:
          A tuple *(data, target*).

          *data* is a two dimensional numpy array with shape n x m
          (one row per example).

          *target* is a one dimensional array with n target values.

          *target* may be ``None`` if there is no target value,
          e.g. in an unsupervised learning setting.

        :rtype: tuple
        """


class CrossValidationGenerator(metaclass=ABCMeta):
    """A :class:`CrossValidationGenerator` provides train/test indices
    to split data in train and validation sets.

    :class:`CrossValidationGenerator` corresponds to the *cross
    validation generator* interface of scikit-learn.
    """

    @abstractmethod
    def __iter__(self):
        """
        :return:
          Tuples of train/test indices.
        """


class Model(BaseEstimator, metaclass=ABCMeta):
    """A :class:`Model` can be :meth:`~Model.fit` to data and can be
    used to :meth:`~Model.predict` data.

    :class:`Model` corresponds to the *estimators* interface of
    scikit-learn.
    """

    @abstractmethod
    def fit(self, X, y=None):
        """Fit to data array *X* and possibly a target array *y*.

        :return: self
        """

    @abstractmethod
    def predict(self, X, **kw):
        """Predict classes for data array *X* with shape n x m.

        Some models may accept additional keyword arguments.

        :return:
          A numpy array of length n with the predicted classes (for
          classification problems) or numeric values (for regression
          problems).

        :raises:
          May raise a :class:`PredictError` to indicate that some
          condition made it impossible to deliver a prediction.
        """

    def predict_proba(self, X, **kw):
        """Predict probabilities for data array *X* with shape n x m.

        :return:
          A numpy array of length n x c with a list class
          probabilities per sample.

        :raises:
          :class:`NotImplementedError` if not applicable.
        """
        raise NotImplementedError()  # pragma: no cover


class PredictError(Exception):
    """Raised by :meth:`Model.predict` to indicate that some condition
    made it impossible to deliver a prediction.
    """
    def __init__(self, error_message, error_code=-1):
        self.error_message = error_message
        self.error_code = error_code

    def __str__(self):
        return "{} ({})".format(self.error_message, self.error_code)


class ModelPersisterMeta(ABCMeta):
    def __init__(cls, name, bases, attrs, **kwargs):
        super().__init__(name, bases, attrs, **kwargs)
        cls.read = PluggableDecorator('read_model_decorators')(cls.read)
        cls.write = PluggableDecorator('write_model_decorators')(cls.write)


class ModelPersister(metaclass=ModelPersisterMeta):
    @abstractmethod
    def read(self, version=None):
        """Returns a :class:`Model` instance.

        :param str version:
          *version* may be used to read a specific version of a model.
          If *version* is ``None``, returns the active model.

        :return:
          The model object.

        :raises:
          LookupError if no model was available.
        """

    @abstractmethod
    def write(self, model):
        """Persists a :class:`Model` and returns a new version number.

        It is the :class:`ModelPersister`'s responsibility to annotate
        the 'version' information onto the model before it is saved.

        The new model will initially be inactive.  Use
        :meth:`ModelPersister.activate` to activate the model.

        :return:
          The new model's version identifier.
        """

    @abstractmethod
    def activate(self, version):
        """Set the model with the given *version* to be the active
        one.

        Implies that any previously active model becomes inactive.

        :param str version:
          The *version* of the model that's activated.

        :raises:
          LookupError if no model with given *version* exists.
        """

    def delete(self, version):
        """Delete the model with the given *version* from the
        database.

        :param str version:
          The *version* of the model that's activated.

        :raises:
          LookupError if no model with given *version* exists.
        """

    @abstractmethod
    def list_models(self):
        """List metadata of all available models.

        :return:
          A list of dicts, with each dict containing information about
          one of the available models.  Each dict is guaranteed to
          contain the ``version`` key, which is the same version
          number that :meth:`ModelPersister.read` accepts for loading
          specific models.
        """

    @abstractmethod
    def list_properties(self):
        """List properties of :class:`ModelPersister` itself.

        :return:
          A dictionary of key and value pairs, where both keys and
          values are of type ``str``.  Properties will usually include
          ``active-model`` and ``db-version`` entries.
        """

    @abstractmethod
    def upgrade(self, from_version=None, to_version=__version__):
        """Upgrade the underlying database to the latest version.

        Newer versions of Palladium may require changes to the
        :class:`ModelPersister`'s database.  This method provides an
        opportunity to run the necessary upgrade steps.

        It's the :class:`ModelPersister`'s responsibility to keep
        track of the Palladium version that was used to create and
        upgrade its database, and thus to determine the upgrade steps
        necessary.
        """


class PredictService(metaclass=ABCMeta):
    """Responsible for producing the output for the '/predict' HTTP
    endpoint.
    """
    @abstractmethod
    def __call__(self, model, request):
        """
        Use the model to run a prediction with the requested data.

        :param model:
          The :class:`~Model` instance to use for making predictions.

        :param request:
          A werkzeug ``request`` object.  A dictionary with query
          parameters is available at *request.values*.

        :return:
          A werkzeug ``response`` object.  It is the
          :class:`PredictService`'s responsiblity to return
          appropriate status codes and data in case of error.
        """
