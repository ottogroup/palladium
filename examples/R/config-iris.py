{
    'service_metadata': {
        'service_name': 'iris',
        'service_version': '0.1',
    },

    'dataset_loader_train': {
        '!': 'palladium.R.DatasetLoader',
        'scriptname': 'iris.R',
        'funcname': 'dataset',
    },

    'dataset_loader_test': {
        '!': 'palladium.R.DatasetLoader',
        'scriptname': 'iris.R',
        'funcname': 'dataset',
    },

    'model': {
        '!': 'palladium.R.ClassificationModel',
        'scriptname': 'iris.R',
        'funcname': 'train.randomForest',
        'encode_labels': True,
    },

    'model_persister': {
        '!': 'palladium.persistence.CachedUpdatePersister',
        'impl': {
            '!': 'palladium.persistence.Database',
            'url': 'sqlite:///iris-model.db',
        },
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
