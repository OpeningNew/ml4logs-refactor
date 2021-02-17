# ===== IMPORTS =====
# === Standard library ===
import logging
import pathlib
import warnings
import json

# === Thirdparty ===
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from pyod.models.lof import LOF
from pyod.models.ocsvm import OCSVM
from pyod.models.iforest import IForest
from pyod.models.pca import PCA
from sklearn.metrics import (roc_auc_score,
                             average_precision_score,
                             precision_recall_fscore_support)


# ===== GLOBALS =====
logger = logging.getLogger(__name__)


# ===== CLASSES =====
class LinearSVCWrapper:
    def __init__(self, **kwargs):
        self._linear_svc = LinearSVC(**kwargs)
        self._clf = CalibratedClassifierCV(self._linear_svc)

    def fit(self, X, Y):
        self._clf.fit(X, Y)
        return self

    def predict(self, X):
        return self._clf.predict(X)

    def predict_proba(self, X):
        return self._clf.predict_proba(X)


# ===== CONSTANTS =====
MODEL_CLASSES = {
    'logistic_regression': LogisticRegression,
    'decision_tree': DecisionTreeClassifier,
    'linear_svc': LinearSVCWrapper,
    'lof': LOF,
    'one_class_svm': OCSVM,
    'isolation_forest': IForest,
    'pca': PCA
}


# ===== FUNCTIONS =====
def train_test_models(args):
    train_path = pathlib.Path(args['train_path'])
    test_path = pathlib.Path(args['test_path'])
    stats_path = pathlib.Path(args['stats_path'])

    stats_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info('Load train dataset from \'%s\'', train_path)
    npzfile_train = np.load(train_path)
    logger.info('Load test dataset from \'%s\'', test_path)
    npzfile_test = np.load(test_path)

    stats = {'step': args, 'metrics': {}}
    for m_dict in args['models']:
        logger.info('=== Use \'%s\' model ===', m_dict['name'])
        model = MODEL_CLASSES[m_dict['name']](**m_dict['args'])

        logger.info('Fit train data to model')
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(npzfile_train['X'], npzfile_train['Y'])

        logger.info('Compute metrics on test data')
        c_pred = model.predict(npzfile_test['X'])
        y_pred = model.predict_proba(npzfile_test['X'])[:, 1]
        auc = roc_auc_score(npzfile_test['Y'], y_pred)
        ap = average_precision_score(npzfile_test['Y'], y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            npzfile_test['Y'], c_pred, average='binary', zero_division=0
        )
        logger.info('AUC = %.2f, AP = %.2f', auc, ap)
        logger.info('Precision = %.2f, Recall = %.2f, F1-score = %.2f',
                    precision, recall, f1)

        stats['metrics'][m_dict['name']] = {'auc': auc,
                                            'ap': ap,
                                            'precision': precision,
                                            'recall': recall,
                                            'f1': f1}

    logger.info('Save metrics into \'%s\'', stats_path)
    stats_path.write_text(json.dumps(stats, indent=4))
