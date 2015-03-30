{
    'service_metadata': {
        'service_name': 'iris',
        'service_version': '0.1',
        },

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
        },

    'model': {
        '__factory__': 'sklearn.linear_model.LogisticRegression',
        'C': 0.3,
        },

    'grid_search': {
        'param_grid': {
            'C': [0.1, 0.3, 1.0],
            },
        'verbose': 4,
        'n_jobs': -1,
        },

    'model_persister': {
        '__factory__': 'palladium.persistence.CachedUpdatePersister',
        'update_cache_rrule': {'freq': 'HOURLY'},
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

    'alive': {
        'process_store_required': ('model',),
        },
}
