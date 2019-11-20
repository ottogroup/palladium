{
    'service_metadata': {
        'service_name': 'iris',
        'service_version': '0.1',
    },

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
    },

    'model': {
        '!': 'sklearn.linear_model.LogisticRegression',
        'C': 0.3,
        'solver': 'lbfgs',
        'multi_class': 'auto',
    },

    'grid_search': {
        'param_grid': {
            'C': [0.1, 0.3, 1.0],
        },
        'return_train_score': True,
        'verbose': 4,
        'n_jobs': -1,
    },

    'model_persister': {
        '!': 'palladium.persistence.CachedUpdatePersister',
        'update_cache_rrule': {'freq': 'HOURLY'},
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

    'alive': {
        'process_store_required': ('model',),
    },
}
