from enum import Enum
import numpy as np


class NormalizeMethod(Enum):
    RMS = 1
    MIN_MAX = 2
    Z_SCORE = 3


def normalize_signal(signal, normalize_method):
    if normalize_method == NormalizeMethod.RMS:
        # RMS normalization to signal
        n = signal.shape[0]
        d = np.sqrt(sum(np.power(signal, 2))/n)
        n_signal = signal/d
        return n_signal, d
    elif normalize_method == NormalizeMethod.MIN_MAX:
        # min-max normalization
        minimum = np.minimum(signal)
        maximum = np.maximum(signal)
        n_signal = (signal-minimum)/(maximum-minimum)

        return n_signal, (minimum, maximum)
    elif normalize_method == NormalizeMethod.Z_SCORE:
        # z-score
        mean = np.mean(signal)
        std = np.std(signal)
        n_signal = (signal-mean)/std

        return n_signal, (mean, std)
    else:
        raise TypeError("Invalide normalization method type.")
