from julia import Julia
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder

from palladium.interfaces import Model
from palladium.util import logger
from palladium.util import timer


def make_bridge():  # pragma: no cover
    with timer(logger.info, "Creating Julia bridge"):
        return Julia()


class AbstractModel(Model):
    def __init__(self, fit_func, predict_func,
                 fit_kwargs=None, predict_kwargs=None,
                 encode_labels=False):
        """
        Instantiates a model with the given *fit_func* and
        *predict_func* written in Julia.

        :param str fit_func:
          The dotted name of the Julia function to use for fitting.
          The function must take as its first two arguments the *X*
          and *y* arrays.  All elements of the optional *fit_kwargs*
          dictionary will be passed on to the Julia function as
          keyword arguments.  The return value of *fit_func* will be
          used as the first argument to *predict_func*.

        :param str predict_func:
          Similar to *fit_func*, this is the dotted name of the Julia
          function used for prediction.  The first argument of this
          function is the return value of *fit_func*.  The second
          argument is the *X* data array.  All elements of the
          optional *fit_kwargs* dictionary will be passed on to the
          Julia function as keyword arguments.  The return value of
          *predict_func* is considered to be the target array *y*.

        :param bool encode_labels:
          If set to *True*, the *y* target array will be automatically
          encoded using a :class:`sklearn.preprocessing.LabelEncoder`,
          which is useful if you have string labels but your Julia
          function only accepts numeric labels.
        """
        self.fit_func = fit_func
        self.predict_func = predict_func
        self.encode_labels = encode_labels
        self.fit_kwargs = fit_kwargs or {}
        self.predict_kwargs = predict_kwargs or {}

    def fit(self, X, y):
        self._initialize_julia()
        if self.encode_labels:
            self.enc_ = LabelEncoder()
            y = self.enc_.fit_transform(y)
        self.fitted_ = self.fit_func_(X.T, y, **self.fit_kwargs)
        return self

    def predict(self, X):
        X = X.astype(float)
        y_pred = self.predict_func_(self.fitted_, X.T, **self.predict_kwargs)
        if self.encode_labels:
            y_pred = self.enc_.inverse_transform(y_pred)
        return y_pred

    def _initialize_julia(self):
        fit_1, fit_2 = self.fit_func.rsplit('.', 1)
        predict_1, predict_2 = self.predict_func.rsplit('.', 1)

        bridge = self.bridge_ = make_bridge()
        bridge.call("import {}".format(fit_1))
        bridge.call("import {}".format(predict_1))
        self.fit_func_ = bridge.eval(self.fit_func)
        self.predict_func_ = bridge.eval(self.predict_func)

    def __getstate__(self):
        state = self.__dict__.copy()

        # Serialize the fitted attribute in Julia:
        iobuf = self.bridge_.eval("IOBuffer()")
        self.bridge_.eval('serialize')(iobuf, self.fitted_)
        iobuf.seek(0)
        state['fitted_'] = iobuf.read()

        del state['fit_func_']
        del state['predict_func_']
        del state['bridge_']

        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._initialize_julia()

        # Deserialize the fitted Julia attribute:
        fitted = state['fitted_']
        iobuf = self.bridge_.eval("IOBuffer()")
        iobuf.write(fitted)
        iobuf.seek(0)
        self.fitted_ = self.bridge_.eval('deserialize')(iobuf)


class ClassificationModel(AbstractModel):
    def score(self, X, y):
        return accuracy_score(self.predict(X), y)
