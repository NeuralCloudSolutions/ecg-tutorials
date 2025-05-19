import random

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages

from data_utils.normalize_signal import normalize_signal, NormalizeMethod
import visualizer.ecg_plot as ecg_plot


class Region:
    def __init__(self, start, end):
        self.start = start
        self.end = end


class Event:
    def __init__(self, tracings, title, region=None):
        self.tracings = tracings
        self.title = title
        self.region = region


def report(
    tracings,
    sampling_rate,
    analysis_data,
    pdf_output_path
):
    leads = tracings.shape[0]
    figsize = (8.3, 11.7)
    figs_per_page = 12//leads
    seconds_per_fig = 15

    chunk_size = int(seconds_per_fig * sampling_rate)
    step = 1.0/sampling_rate
    time_x = np.arange(0, chunk_size*step, step)

    page = plt.figure(figsize=figsize)

    with PdfPages(pdf_output_path) as pdf:

        # Plots
        grid_plots = gridspec.GridSpec(
            2, 1, wspace=0.2, hspace=0.2)

        ax0 = plt.Subplot(page, grid_plots[0])
        ax1 = plt.Subplot(page, grid_plots[1])

        stats = analysis_data["stats"]
        rr_histogram = stats["rr_histogram"]
        qtc_histogram = stats["qtc_histogram"]

        hr_start = rr_histogram["s"]
        hr_end = rr_histogram["e"]
        x = list(range(hr_start, hr_end+2))
        y = rr_histogram["bins"]
        ax0.stairs(y, x, fill=True)
        ax0.set_title("RR (ms)")

        qtc_start = qtc_histogram["s"]
        qtc_end = qtc_histogram["e"]
        x = list(range(qtc_start, qtc_end+2))
        y = qtc_histogram["bins"]
        ax1.stairs(y, x, fill=True)
        ax1.set_title("QTc (ms)")

        page.add_subplot(ax0)
        page.add_subplot(ax1)

        pdf.savefig(page)
        plt.close()

        events = analysis_data["events"]
        py_events = []

        page = plt.figure(figsize=figsize)
        grid_sections = gridspec.GridSpec(
            figs_per_page, 1, wspace=0.2, hspace=0.5)

        figs_on_page = 0
        all_events = []

        min_hr_events = events["lowest_hr"]
        max_hr_events = events["highest_hr"]

        if len(min_hr_events) > 0:
            hr_event = min_hr_events[0]
            hr = hr_event["hr"]

            all_events.append((f"Minimum HR ({hr})", hr_event))

        if len(max_hr_events) > 0:
            hr_event = max_hr_events[0]
            hr = hr_event["hr"]

            all_events.append((f"Maximum HR ({hr})", hr_event))

        afib_events = events["afib"]
        bradycardia_events = events["bradycardia"]
        tachycardia_events = events["tachycardia"]

        if len(afib_events) <= 5:
            for event in afib_events:
                all_events.append(("AFIB", event))
        else:
            for event in random.choices(afib_events, k=5):
                all_events.append(("AFIB", event))

        top_bradycardia_events = []
        top_tachycardia_events = []
        for event in bradycardia_events:
            top_bradycardia_events.append((
                event["hr"],
                "Bradycardia: Mean {} BPM".format(event["hr"]),
                event))
        for event in tachycardia_events:
            top_tachycardia_events.append((
                event["hr"],
                "Tachycardia: Mean {} BPM".format(event["hr"]),
                event))

        top_bradycardia_events = sorted(
            top_bradycardia_events, key=lambda tup: tup[0])
        top_tachycardia_events = sorted(
            top_tachycardia_events, key=lambda tup: tup[0], reverse=True)

        if len(top_bradycardia_events) <= 5:
            for _, title, event in top_bradycardia_events:
                all_events.append((title, event))
        else:
            for i in range(5):
                _, title, event = top_bradycardia_events[i]
                all_events.append((title, event))

        if len(top_tachycardia_events) <= 5:
            for _, title, event in top_tachycardia_events:
                all_events.append((title, event))
        else:
            for i in range(5):
                _, title, event = top_tachycardia_events[i]
                all_events.append((title, event))

        for title, event in all_events:
            start = event["s"]
            end = event["e"]

            start_idx = sampling_rate * start / 1000.0
            end_idx = sampling_rate * end / 1000.0

            start_idx = int(np.clip(start_idx, 0, tracings.shape[1] - 1))
            end_idx = int(np.clip(end_idx, 0, tracings.shape[1] - 1))

            # Greater than 5 min
            chunks = 1
            if (end - start > 5*60*1000):
                chunks = 5

            for _ in range(chunks):
                if (end_idx-chunk_size < start_idx):
                    chunk_idx = start_idx
                else:
                    chunk_idx = np.random.randint(
                        start_idx, end_idx-chunk_size)

                chunk_start = chunk_idx / 250.0
                chunk_end = chunk_start + seconds_per_fig

                tracing_chunk = tracings[:, chunk_idx:(chunk_idx+chunk_size)]

                py_events.append(
                    Event(
                        tracing_chunk,
                        "{}: {:.2f} to {:.2f} seconds - Strip {:.2f} to {:.2f} seconds".format(
                            title, start / 1000.0, end / 1000.0, chunk_start, chunk_end)
                    )
                )

        pauses_events = events["pauses"]
        if len(pauses_events) > 5:
            pauses_events = random.choices(pauses_events, k=5)

        for pauses_event in pauses_events:
            start = pauses_event["s"]
            end = pauses_event["e"]
            duration = pauses_event["d"]

            beat_start_idx = sampling_rate * start / 1000.0
            beat_end_idx = np.clip(
                sampling_rate * end / 1000.0, beat_start_idx, beat_start_idx+chunk_size)

            start_idx = int(np.clip(beat_start_idx - 2*sampling_rate,
                            0, tracings.shape[1] - 1))
            end_idx = int(np.clip(start_idx+chunk_size,
                                  0, tracings.shape[1] - 1))

            chunk_start = start_idx / 250.0
            chunk_end = chunk_start + seconds_per_fig

            tracing_chunk = tracings[:, start_idx:end_idx]

            py_events.append(
                Event(
                    tracing_chunk,
                    "Pause duration of {:d} milliseconds - Strip {:.2f} to {:.2f} seconds".format(
                        duration, chunk_start, chunk_end),
                    Region(
                        (beat_start_idx - start_idx) / 250.0,
                        (beat_end_idx - start_idx) / 250.0,
                    )
                )
            )

        pac_events = events["pac"]
        pvc_events = events["pvc"]
        beat_events = []
        pac_beat_events = []
        pvc_beat_events = []

        for event in pac_events:
            pac_beat_events.append(
                Region(
                    event["s"],
                    event["e"]
                ))

        for event in pvc_events:
            pvc_beat_events.append(
                Region(
                    event["s"],
                    event["e"]
                ))

        pac_beat_events = sorted(pac_beat_events, key=lambda x: x.start)
        pvc_beat_events = sorted(pvc_beat_events, key=lambda x: x.start)

        # Group PAC and PVC events
        pac_beat_event_idx = 0
        while pac_beat_event_idx < len(pac_beat_events):
            first_pac_start = pac_beat_events[pac_beat_event_idx].start
            next_beat_event_idx = pac_beat_event_idx + 1

            while next_beat_event_idx < len(pac_beat_events):
                last_pac_end = pac_beat_events[next_beat_event_idx].end
                if (last_pac_end - first_pac_start) > 12000:
                    break
                next_beat_event_idx += 1

            beat_events.append((
                'PAC',
                pac_beat_events[pac_beat_event_idx:next_beat_event_idx]
            ))

            pac_beat_event_idx = next_beat_event_idx

        pvc_beat_event_idx = 0
        while pvc_beat_event_idx < len(pvc_beat_events):
            first_pvc_start = pvc_beat_events[pvc_beat_event_idx].start
            next_beat_event_idx = pvc_beat_event_idx + 1

            while next_beat_event_idx < len(pvc_beat_events):
                last_pvc_end = pvc_beat_events[next_beat_event_idx].end
                if (last_pvc_end - first_pvc_start) > 12000:
                    break
                next_beat_event_idx += 1

            beat_events.append((
                'PVC',
                pvc_beat_events[pvc_beat_event_idx:next_beat_event_idx]
            ))

            pvc_beat_event_idx = next_beat_event_idx

        if len(beat_events) > 5:
            beat_events = random.choices(beat_events, k=5)

        for title, regions in beat_events:
            start = regions[0].start
            end = regions[-1].end

            beat_start_idx = sampling_rate * start / 1000.0
            beat_end_idx = np.clip(
                sampling_rate * end / 1000.0, beat_start_idx, beat_start_idx+chunk_size)

            start_idx = int(np.clip(beat_start_idx - 2*sampling_rate,
                            0, tracings.shape[1] - 1))
            end_idx = int(np.clip(start_idx+chunk_size,
                                  0, tracings.shape[1] - 1))

            chunk_start = start_idx / 250.0
            chunk_end = chunk_start + seconds_per_fig

            tracing_chunk = tracings[:, start_idx:end_idx]

            py_events_regions = []

            for region in regions:
                start = region.start
                end = region.end

                beat_start_idx = sampling_rate * start / 1000.0
                beat_end_idx = np.clip(
                    sampling_rate * end / 1000.0, beat_start_idx, beat_start_idx+chunk_size)

                py_events_regions.append(
                    Region(
                        (beat_start_idx - start_idx) / 250.0,
                        (beat_end_idx - start_idx) / 250.0,
                    ))

            py_events.append(
                Event(
                    tracing_chunk,
                    "{} - Strip {:.2f} to {:.2f} seconds".format(
                        title, chunk_start, chunk_end),
                    py_events_regions

                )
            )

        for event in py_events:
            if figs_on_page >= figs_per_page:
                # Save figure
                pdf.savefig(page)
                plt.close()
                page = plt.figure(figsize=figsize)

                grid_sections = gridspec.GridSpec(
                    figs_per_page, 1, wspace=0.2, hspace=0.5)

                figs_on_page = 0

            grid_leads = gridspec.GridSpecFromSubplotSpec(leads, 1,
                                                          subplot_spec=grid_sections[figs_on_page], wspace=0.1, hspace=0.0)
            figs_on_page += 1

            for lead in range(leads):
                ax = plt.Subplot(page, grid_leads[lead])
                ecg_plot.ax_plot_grid(
                    ax, seconds_per_fig, amplitude_ecg=1.8, alpha=0.1)
                if event.region is not None:
                    if isinstance(event.region, list):
                        for region in event.region:
                            ecg_plot.ax_plot_region(
                                ax, region.start, region.end, alpha=0.5)
                    else:
                        ecg_plot.ax_plot_region(
                            ax, event.region.start, event.region.end, alpha=0.5)

                tracing_chunk = event.tracings[lead]
                if len(tracing_chunk) < chunk_size:
                    tmp = np.zeros(chunk_size)
                    tmp[:len(tracing_chunk)] = tracing_chunk
                    tracing_chunk = tmp

                tracing_chunk, _ = normalize_signal(
                    tracing_chunk, NormalizeMethod.Z_SCORE)

                ecg_plot.ax_plot_signal(ax, time_x, tracing_chunk,
                                        linewidth=0.7, color='black', alpha=1.0)

                ax.set_xticklabels([])
                ax.set_yticklabels([])

                if lead == 0:
                    ax.set_title(
                        event.title,
                        loc='left', fontsize=5)

                page.add_subplot(ax)

        pdf.savefig(page)
    plt.close()
