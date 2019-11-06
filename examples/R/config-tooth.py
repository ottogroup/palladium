{
    'service_metadata': {
        'service_name': 'tooth',
        'service_version': '0.1',
    },

    'dataset_loader_train': {
        '!': 'palladium.R.DatasetLoader',
        'scriptname': 'tooth.R',
        'funcname': 'dataset',
    },

    'dataset_loader_test': {
        '!': 'palladium.R.DatasetLoader',
        'scriptname': 'tooth.R',
        'funcname': 'dataset',
    },

    'model': {
        '!': 'sklearn.pipeline.Pipeline',
        'steps': [
            ['rpy2', {
                '!': 'palladium.R.Rpy2Transform',
            }],
            ['regressor', {
                '!': 'palladium.R.RegressionModel',
                'scriptname': 'tooth.R',
                'funcname': 'train.randomForest',
            }],
        ],
    },

    'model_persister': {
        '!': 'palladium.persistence.CachedUpdatePersister',
        'impl': {
            '!': 'palladium.persistence.Database',
            'url': 'sqlite:///tooth-model.db',
        },
    },

    'predict_service': {
        '!': 'palladium.server.PredictService',
        'mapping': [
            ('supp', 'str'),
            ('dose', 'float'),
        ],
    },
}
