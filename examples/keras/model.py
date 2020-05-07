from dstoolbox.pipeline import PipelineY
from keras.models import Sequential
from keras.layers import Dense
from keras.wrappers.scikit_learn import KerasClassifier
import numpy as np
from sklearn.preprocessing import LabelBinarizer


np.random.seed(0)


def keras_model():
    model = Sequential()
    model.add(Dense(8, input_dim=4, activation='relu'))
    model.add(Dense(3, activation='softmax'))
    model.compile(
        loss='categorical_crossentropy',
        optimizer='adam',
        metrics=['accuracy'],
        )
    return model


def make_pipeline(**kw):
    # In the case of this Iris dataset, our targets are string labels,
    # and KerasClassifier doesn't like that.  So we transform the
    # targets into a one-hot encoding instead using PipeLineY.
    return PipelineY([
            ('clf', KerasClassifier(build_fn=keras_model, **kw)),
        ],
        y_transformer=LabelBinarizer(),
        predict_use_inverse=False,
        )
