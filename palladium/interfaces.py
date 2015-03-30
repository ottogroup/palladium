"""Interfaces defining the behaviour of Palladium's components.
"""

from abc import abstractmethod
from abc import ABCMeta

from sklearn.base import BaseEstimator


def annotate(obj, metadata=None):
    base_metadata = getattr(obj, '__metadata__', {})
    if metadata is not None:
        base_metadata.update(metadata)
        obj.__metadata__ = base_metadata
    return obj.__metadata__


class DatasetLoader(metaclass=ABCMeta):
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


class ModelPersister(metaclass=ABCMeta):
    @abstractmethod
    def read(self, version=None):
        """Returns a :class:`Model` instance.

        :param str version:
          *version* may be used to read a specific version of a model.
          If *version* is ``None``, returns the latest model.

        :return:
          The model object.

        :raises:
          IOError if no model was available.
        """

    @abstractmethod
    def write(self, model):
        """Persists a :class:`Model` and returns a new version number.

        It is the :class:`ModelPersister`'s responsibility to annotate
        the 'version' information onto the model before it is saved.
        """

    @abstractmethod
    def list(self):
        """List metadata of all available models.

        :return:
          A list of dicts, with each dict containing information about
          one of the available models.  Each dict is guaranteed to
          contain the ``version`` key, which is the same version
          number that :meth:`ModelPerister.read` accepts for loading
          specific models.
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
          parameters is available at *request.args*.

        :return:
          A werkzeug ``response`` object.  It is the
          :class:`PredictService`'s responsiblity to return
          appropriate status codes and data in case of error.
        """
