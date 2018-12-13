{
    'service_metadata': {
        'service_name': 'tooth',
        'service_version': '0.1',
    },

    'dataset_loader_train': {
        '__factory__': 'palladium.R.DatasetLoader',
        'scriptname': 'tooth.R',
        'funcname': 'dataset',
    },

    'dataset_loader_test': {
        '__factory__': 'palladium.R.DatasetLoader',
        'scriptname': 'tooth.R',
        'funcname': 'dataset',
    },

    'model': {
        '__factory__': 'sklearn.pipeline.Pipeline',
        'steps': [
            ['rpy2', {
                '__factory__': 'palladium.R.Rpy2Transform',
            }],
            ['regressor', {
                '__factory__': 'palladium.R.RegressionModel',
                'scriptname': 'tooth.R',
                'funcname': 'train.randomForest',
            }],
        ],
    },

    'model_persister': {
        '__factory__': 'palladium.persistence.CachedUpdatePersister',
        'impl': {
            '__factory__': 'palladium.persistence.Database',
            'url': 'sqlite:///tooth-model.db',
        },
    },

    'predict_service': {
        '__factory__': 'palladium.server.PredictService',
        'mapping': [
            ('supp', 'str'),
            ('dose', 'float'),
        ],
    },
}
