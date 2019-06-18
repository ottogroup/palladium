# Use this file in conjunction with config-iris.py by setting:
#
#   export PALLADIUM_CONFIG=config-iris.py,config-iris-dataset-from-python.py

{
    'dataset_loader_train': {
        '__factory__': 'palladium.dataset.CSV',
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
        '__copy__': 'dataset_loader_train',
        'skiprows': 100,
        'nrows': None,
    },
}
