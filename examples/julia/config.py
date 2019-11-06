{
    'dataset_loader_train': {
        '!': 'palladium.dataset.CSV',
        'path': 'iris.data',
        'names': [
            'sepal length',
            'sepal width',
            'petal length',
            'petal width',
            'species',
        ],
        'target_column': 'species',
        'nrows': 100,
        'converters': {'species': lambda x: 1 if x == 'Iris-setosa' else -1},
    },

    'dataset_loader_test': {
        '!': 'palladium.dataset.CSV',
        'path': 'iris.data',
        'names': [
            'sepal length',
            'sepal width',
            'petal length',
            'petal width',
            'species',
        ],
        'target_column': 'species',
        'skiprows': 100,
        'converters': {'species': lambda x: 1 if x == 'Iris-setosa' else -1},
    },

    'model': {
        '!': 'palladium.julia.ClassificationModel',
        'fit_func': 'SVM.svm',
        'predict_func': 'SVM.predict',
    },

    'model_persister': {
        '!': 'palladium.persistence.Database',
        'url': 'sqlite:///iris-model.db',
    },

    'predict_service': {
        '!': 'palladium.server.PredictService',
        'mapping': [
            ('sepal length', 'float'),
            ('sepal width', 'float'),
            ('petal length', 'float'),
            ('petal width', 'float'),
        ],
    },
}
