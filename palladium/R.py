"""Support for building models using the R programming language.
"""

from palladium.interfaces import DatasetLoader
from palladium.interfaces import Model
import numpy as np
from pandas import DataFrame
from pandas import Series
from rpy2 import robjects
from rpy2.robjects import pandas2ri
from rpy2.robjects.pandas2ri import py2ri
from rpy2.robjects.numpy2ri import numpy2ri
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder


pandas2ri.activate()


class ObjectMixin:
    r = robjects.r

    def __init__(self, scriptname, funcname, **kwargs):
        self.scriptname = scriptname
        self.funcname = funcname
        self.r.source(scriptname)
        self.rfunc = self.r[funcname]
        self.kwargs = kwargs


class DatasetLoader(DatasetLoader, ObjectMixin):
    """A :class:`~palladium.interfaces.DatasetLoader` that calls an R
    function to load the data.
    """
    def __call__(self):
        X, y = self.rfunc(**self.kwargs)
        return X, y


class AbstractModel(Model, ObjectMixin):
    def __init__(self, encode_labels=False, *args, **kwargs):
        super(Model, self).__init__(*args, **kwargs)
        self.encode_labels = encode_labels

    @staticmethod
    def _from_python(obj):
        if isinstance(obj, DataFrame):
            obj = py2ri(obj)
        elif isinstance(obj, Series):
            obj = numpy2ri(obj.values)
        elif isinstance(obj, np.ndarray):
            obj = numpy2ri(obj)
        return obj

    def fit(self, X, y=None):
        if self.encode_labels:
            self.enc_ = LabelEncoder()
            y = self.enc_.fit_transform(y)

        self.rmodel_ = self.rfunc(
            self._from_python(X),
            self._from_python(y),
            **self.kwargs)


class ClassificationModel(AbstractModel):
    """A :class:`~palladium.interfaces.Model` for classification problems
    that uses an R model for training and prediction.
    """

    def predict_proba(self, X):
        X = self._from_python(X)
        return np.asarray(self.r['predict'](self.rmodel_, X, type='prob'))

    def predict(self, X):
        X = X.astype(float) if hasattr(X, 'astype') else X
        y_pred = np.argmax(self.predict_proba(X), axis=1)
        if self.encode_labels:
            y_pred = self.enc_.inverse_transform(y_pred)
        return y_pred

    def score(self, X, y):
        return accuracy_score(self.predict(X), np.asarray(y))
