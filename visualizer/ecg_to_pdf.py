from tqdm import tqdm
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages

import visualizer.ecg_plot as ecg_plot
from data_utils.normalize_signal import normalize_signal, NormalizeMethod


def start_index_gen(tracing_length, chunk_size, num_of_figs):
    if tracing_length is None:
        yield from [0]*num_of_figs

    # Yield starting indexes in order
    elif chunk_size * num_of_figs >= tracing_length:
        yield from range(0, tracing_length, chunk_size)

    # Yield random starting points
    else:
        yield from np.sort(np.random.randint(
            0, tracing_length - chunk_size, num_of_figs))


def ecg_to_pdf(sampling_rate: float, output_path: str, tracings, labels=None, lead_names=None, max_pages: int = -1):
    """
    **Converts tracings, reconstructions, and/or labels into a pdf**

    Function to create a pdf that shows sections of an ecg, with the original tracings, the cleaned
    reconstruction, and the ecg's labels. 

    Parameters
    ----------
    sampling_rate : float
        The sampling rate of the given ecg in Hz.
    output_path : str
        The path where the pdf is saved to.
    tracings : Union[None, np.array, list]
        A 2D-array of the original ecg signal. The first axis represents the different leads. The
        second axis represents samples across time.
        If None is given then no tracings will be plotted.
    labels: Union[None, np.array, list]
        A 1D-array of the labels across time. This must have the same size as tracings and reconstructions'
        second axis, if labels is not None and either tracings or reconstructions are not None.
        0 represents no wave, 1 represents a P-wave, 2 represents a QRS complex, 3 represents a T-wave.
        If None is given then no labels will be plotted.
    lead_names : Union[None, list]
        The names of each lead.
        If None is given then all lead names will be empty strings
    max_pages : int
        The maximum number of pages the pdf can be. If the full tracing cannot fit in the under max_pages
        pages, then only random samples of the ecg will be selected.
    """
    if sampling_rate <= 0:
        raise ValueError("Sampling rate must be positive")

    elif 1000 < sampling_rate:
        raise ValueError("Sampling rate must not be greater than 1000")

    # Check that values are lists/numpy arrays
    if isinstance(tracings, list):
        tracings = np.array(tracings)

    elif not isinstance(tracings, np.ndarray):
        raise ValueError("tracings dtype not recognized")

    if isinstance(labels, list):
        labels = np.array(labels)

    elif labels is not None and not isinstance(labels, np.ndarray):
        raise ValueError("labels dtype not recognized")

    if (not isinstance(lead_names, list) and
        not isinstance(lead_names, np.ndarray) and
            lead_names is not None):
        raise ValueError("lead names must be a list or numpy array")

    # Check that values have the correct dimensions
    if tracings.ndim != 2:
        raise ValueError(
            f"tracings must be 2-dimensional. Got {tracings.ndim} dimension(s)")

    elif labels is not None and labels.ndim != 1:
        raise ValueError(
            f"labels must be 1-dimensional. Got {labels.ndim} dimensions")

    elif (labels is not None and
          tracings.shape[1] != labels.shape[0]):
        raise ValueError(
            f"tracing's shape is {tracings.shape} which is incompatible with label's shape {labels.shape}")

    n_leads = tracings.shape[0]
    tracing_length = tracings.shape[1]
    seconds = float(tracing_length) / sampling_rate

    if lead_names is None:
        lead_names = [""]*n_leads

    elif len(lead_names) != n_leads:
        raise ValueError(
            f"Number of leads is {n_leads}, but {len(lead_names)} lead names given.")

    labels_one_hot = np.zeros((tracing_length, 4), dtype=np.uint8)
    labels_one_hot[np.arange(tracing_length), labels] = 1

    figsize = (8.3, 11.7)
    figs_per_page = 12 // n_leads
    seconds_per_fig = 15

    if max_pages > 0 and seconds is None:
        num_pages = max_pages
        num_of_figs = max_pages * figs_per_page

    elif max_pages > 0:
        num_of_figs = np.ceil(seconds / seconds_per_fig)
        num_pages = np.ceil(num_of_figs / figs_per_page)
        num_pages = min(num_pages, max_pages)
        num_of_figs = min(num_of_figs, max_pages * figs_per_page)

    elif seconds is not None:
        num_of_figs = np.ceil(seconds / seconds_per_fig)
        num_pages = np.ceil(num_of_figs / figs_per_page)

    else:
        raise ValueError("No data or maximum pages given")

    num_of_figs = int(num_of_figs)
    num_pages = int(num_pages)

    chunk_size = int(seconds_per_fig * sampling_rate)

    step = 1.0/sampling_rate
    time_x = np.arange(0, chunk_size*step, step)

    # Create pages
    gen = start_index_gen(tracing_length, chunk_size, num_of_figs)
    with PdfPages(output_path) as pdf:
        for page_i in tqdm(range(num_pages)):
            page = plt.figure(figsize=figsize)

            # Only add as many figures as are needed
            page_figures = min(figs_per_page, num_of_figs -
                               page_i * figs_per_page)
            grid_sections = gridspec.GridSpec(
                page_figures, 1, wspace=0.2, hspace=0.2)

            for i in range(page_figures):
                grid_leads = gridspec.GridSpecFromSubplotSpec(n_leads, 1,
                                                              subplot_spec=grid_sections[i], wspace=0.1, hspace=0.0)

                start = next(gen)
                end = start + chunk_size

                for lead in range(n_leads):
                    ax = plt.Subplot(page, grid_leads[lead])

                    if tracings is not None:
                        tracing_chunk = tracings[lead, start:end]
                        tracing_chunk, _ = normalize_signal(
                            tracing_chunk, NormalizeMethod.Z_SCORE)
                        if len(tracing_chunk) < chunk_size:
                            tmp = np.zeros(chunk_size)
                            tmp[:len(tracing_chunk)] = tracing_chunk
                            tracing_chunk = tmp

                    ecg_plot.ax_plot_grid(
                        ax, seconds_per_fig, amplitude_ecg=1.8, alpha=0.1)

                    if labels_one_hot is not None:
                        labels_chunk = labels_one_hot[start:end]
                        if len(labels_chunk) < chunk_size:
                            tmp = np.zeros((chunk_size, 4), dtype=np.uint8)
                            tmp[:len(labels_chunk)] = labels_chunk
                            labels_chunk = tmp

                        ecg_plot.ax_plot_pqrst(
                            ax, time_x, labels_chunk, alpha=0.75)

                    tracing_chunk -= tracing_chunk.mean()
                    upper_limit = max(tracing_chunk)
                    lower_limit = min(tracing_chunk)
                    scaling_factor = 2 * 1.65 / (upper_limit - lower_limit)

                    tracing_chunk = tracing_chunk * scaling_factor
                    ecg_plot.ax_plot_signal(ax, time_x, tracing_chunk,
                                            linewidth=0.7, color='black', alpha=1.0)

                    ax.set_xticklabels([])
                    ax.set_yticklabels([])

                    ax.set_ylabel(lead_names[lead])

                    page.add_subplot(ax)

            # Save figure
            pdf.savefig(page)
            plt.close()
