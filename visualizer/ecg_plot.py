import numpy as np
from matplotlib.ticker import AutoMinorLocator
from math import ceil


def ax_plot_grid(ax, secs=10, amplitude_ecg=1.8, time_ticks=0.2, alpha=0.25):
    ax.set_xticks(np.arange(0, secs + 1, time_ticks))
    ax.set_yticks(np.arange(-ceil(amplitude_ecg), ceil(amplitude_ecg), 0.5))

    ax.minorticks_on()

    ax.xaxis.set_minor_locator(AutoMinorLocator(5))

    ax.set_ylim(-amplitude_ecg, amplitude_ecg)
    ax.set_xlim(0, secs)

    ax.grid(which='major', linestyle='-',
            linewidth='1.0', color='red', alpha=alpha)
    ax.grid(which='minor', linestyle='-', linewidth='1.0',
            color=(1, 0.7, 0.7), alpha=alpha)


def ax_plot_signal(ax, x, y, **kwargs):
    ax.plot(x, y, **kwargs)


def ax_plot_pqrst(ax, x, labels, alpha=0.25):
    samples = labels.shape[0]
    for i in range(samples - 1):
        label = np.argmax(labels[i])

        if label == 0:
            continue

        x0 = x[i]
        x1 = x[i+1]

        # P
        if label == 1:
            ax.axvspan(x0, x1, color='green', alpha=alpha)

        # QRS
        if label == 2:
            ax.axvspan(x0, x1, color='red', alpha=alpha)

        # T
        if label == 3:
            ax.axvspan(x0, x1, color='blue', alpha=alpha)
