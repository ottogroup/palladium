{
    'dataset_loader_train': {
        '__factory__': 'palladium.dataset.Table',
        'path': 'iris.data',
        'names': [
            'sepal length',
            'sepal width',
            'petal length',
            'petal width',
            'species',
            ],
        'target_column': 'species',
        'sep': ',',
        'nrows': 100,
        'converters': {'species': lambda x: 1 if x == 'Iris-setosa' else -1},
        },

    'dataset_loader_test': {
        '__factory__': 'palladium.dataset.Table',
        'path': 'iris.data',
        'names': [
            'sepal length',
            'sepal width',
            'petal length',
            'petal width',
            'species',
            ],
        'target_column': 'species',
        'sep': ',',
        'skiprows': 100,
        'converters': {'species': lambda x: 1 if x == 'Iris-setosa' else -1},
        },

    'model': {
        '__factory__': 'palladium.julia.ClassificationModel',
        'fit_func': 'SVM.svm',
        'predict_func': 'SVM.predict',
        },

    'model_persister': {
        '__factory__': 'palladium.persistence.Database',
        'url': 'sqlite:///iris-model.db',
        },

    'predict_service': {
        '__factory__': 'palladium.server.PredictService',
        'mapping': [
            ('sepal length', 'float'),
            ('sepal width', 'float'),
            ('petal length', 'float'),
            ('petal width', 'float'),
            ],
        },
}
