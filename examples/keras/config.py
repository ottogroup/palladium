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
    },

    'dataset_loader_test': {
        '__copy__': 'dataset_loader_train',
        'nrows': None,
        'skiprows': 100,
    },

    'model': {
        '__factory__': 'model.make_pipeline',
        'epochs': 100,
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

    'service_metadata': {
        'service_name': 'iris',
        'service_version': '0.1',
    },

    'alive': {
        'process_store_required': ('model',),
    },
}
