{
    'service_metadata': {
        'service_name': 'iris',
        'service_version': '0.1',
        },

    'dataset_loader_train': {
        '__factory__': 'palladium.R.DatasetLoader',
        'scriptname': 'iris.R',
        'funcname': 'dataset',
        },

    'dataset_loader_test': {
        '__factory__': 'palladium.R.DatasetLoader',
        'scriptname': 'iris.R',
        'funcname': 'dataset',
        },

    'model': {
        '__factory__': 'palladium.R.ClassificationModel',
        'scriptname': 'iris.R',
        'funcname': 'train.randomForest',
        'encode_labels': True,
        },

    'model_persister': {
        '__factory__': 'palladium.persistence.CachedUpdatePersister',
        'impl': {
            '__factory__': 'palladium.persistence.Database',
            'url': 'sqlite:///iris-model.db',
            },
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
