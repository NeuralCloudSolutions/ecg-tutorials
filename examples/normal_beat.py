"""Find the record's normal beat from the beat encodings and plot it.

    python examples/normal_beat.py --h5 out/report.h5 --edf my.edf
    python examples/normal_beat.py --h5 out/report.h5 --edf my.edf --lead 2 --n 50 --out out/normal_beat.png

Every beat on every lead has a 16-d encoding of its shape (docs/BEAT_ENCODING.md).
The dominant shape of the record is the centroid of the encodings (see
`report_h5.normal_centroid`). The `--n` beats closest to it are cut from the
EDF, aligned on the QRS onset, and averaged.

The H5 report has no tracings, so the EDF that was analyzed is needed. If the
analysis was run with --leads, pass the same --leads here.
"""
import argparse

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import report_h5

parser = argparse.ArgumentParser(description='Plot the average of the beats closest to the normal beat shape.')
parser.add_argument('--h5', type=str, required=True, help='path to report.h5')
parser.add_argument('--edf', type=str, required=True, help='path to the EDF that was analyzed')
parser.add_argument('--leads', type=str, default='',
                    help='the --leads the analysis was run with (default: all)')
parser.add_argument('--lead', type=int, default=1,
                    help='lead to use, 1-based position among the analyzed leads')
parser.add_argument('--n', type=int, default=50, help='number of closest beats to average')
parser.add_argument('--pre-ms', type=int, default=300, help='window before the QRS onset')
parser.add_argument('--post-ms', type=int, default=700, help='window after the QRS onset')
parser.add_argument('--out', type=str, default='out/normal_beat.png', help='output image')
args = parser.parse_args()

lead = args.lead - 1

#
# 1. The normal shape, and the beats closest to it
#
index, encoding = report_h5.encoded_beats(args.h5, lead)
centroid = report_h5.normal_centroid(encoding)

# Encodings are unit vectors, so the dot product is the cosine similarity
similarity = encoding @ centroid
order = np.argsort(-similarity)

#
# 2. Cut the closest beats out of the signal, aligned on the QRS onset
#
beats = report_h5.read_beat_list(args.h5)
signal, mv_per_unit = report_h5.load_lead(
    args.edf, report_h5.edf_lead(report_h5.parse_leads(args.leads), lead))
scale, unit = (mv_per_unit, 'mV') if np.isfinite(mv_per_unit) else (1.0, 'signal units')

pre = report_h5.ms_to_sample(args.pre_ms)
post = report_h5.ms_to_sample(args.post_ms)

windows = []
used = []  # positions in `index` of the beats averaged
for k in order:
    if len(windows) == args.n:
        break
    i = index[k]
    onset = report_h5.ms_to_sample(beats[i].qrs.start)
    # Skip beats whose window runs off the recording; take the next closest
    if onset - pre < 0 or onset + post > len(signal):
        continue
    used.append(k)
    baseline = report_h5.beat_baseline(signal, beats[i])
    window = (signal[onset - pre:onset + post] - baseline) * scale

    # Blank the neighbouring beats so they do not smear the average
    if i > 0:
        prev_end = report_h5.ms_to_sample(beats[i - 1].end) - (onset - pre)
        window[:max(0, prev_end)] = np.nan
    if i + 1 < len(beats):
        next_onset = report_h5.ms_to_sample(beats[i + 1].qrs.start) - (onset - pre)
        window[max(0, next_onset):] = np.nan
    windows.append(window)
windows = np.array(windows)
closest = index[used]

print(f'{len(index)} encoded good-quality beats on lead {args.lead}')
print(f'Cosine similarity to the normal shape of the {len(closest)} closest: '
      f'{similarity[used].min():.4f} .. {similarity[used].max():.4f}')

# Average where at least half of the beats have signal
enough = np.sum(np.isfinite(windows), axis=0) >= len(windows) / 2
average = np.full(windows.shape[1], np.nan)
average[enough] = np.nanmean(windows[:, enough], axis=0)

# Median landmarks of the same beats, relative to the QRS onset. A wave is
# only part of the normal beat when most of the beats have it: in AF, a P wave
# found on one or two beats says nothing about the typical beat.
def median_wave(waves, onsets):
    """(start, end, count) of the median wave, or None if under half the beats have one."""
    present = [(w.start - o, w.end - o) for w, o in zip(waves, onsets) if w is not None]
    if len(present) < len(waves) / 2:
        return None
    starts, ends = zip(*present)
    return float(np.median(starts)), float(np.median(ends)), len(present)

chosen = [beats[i] for i in closest]
onsets_chosen = [b.qrs.start for b in chosen]
landmarks = {
    'P': median_wave([b.p for b in chosen], onsets_chosen),
    'QRS': median_wave([b.qrs for b in chosen], onsets_chosen),
    'T': median_wave([b.t for b in chosen], onsets_chosen),
}

#
# 3. Plot
#
fig, (ax, ax_sim) = plt.subplots(2, 1, figsize=(10, 8), height_ratios=[3, 1])

t_ms = (np.arange(-pre, post) * 1000 / report_h5.SAMPLING_RATE)
for w in windows:
    ax.plot(t_ms, w, color='0.7', linewidth=0.6)
ax.plot(t_ms, average, color='black', linewidth=2, label=f'average of {len(windows)} beats')

colors = {'P': 'tab:green', 'QRS': 'tab:red', 'T': 'tab:blue'}
for name, wave in landmarks.items():
    if wave is None:
        print(f'No {name} wave: fewer than half of the beats have one')
        continue
    start, end, count = wave
    ax.axvspan(start, end, color=colors[name], alpha=0.12,
               label=f'{name} (median of {count} beats)')

ax.axhline(0, color='0.5', linewidth=0.5)
ax.set_xlabel('ms from QRS onset')
ax.set_ylabel(unit)
ax.set_title(f'Normal beat, lead {args.lead}: the {len(windows)} beats closest to the dominant shape')
ax.legend(loc='upper right')

# Similarity of every beat over time: ectopic or noisy beats drop out
onsets_ms = np.array([beats[i].qrs.start for i in index])
if onsets_ms[-1] < 3_600_000:
    onsets, time_unit = onsets_ms / 1000, 'seconds'
else:
    onsets, time_unit = onsets_ms / 3_600_000, 'hours'
ax_sim.scatter(onsets, similarity, s=2, color='0.5', label='encoded beats')
ax_sim.scatter(onsets[used], similarity[used], s=8,
               color='black', label=f'closest {len(used)}')
ax_sim.set_xlabel(f'{time_unit} from start')
ax_sim.set_ylabel('cosine similarity')
ax_sim.legend(loc='lower right')

fig.tight_layout()
fig.savefig(args.out, dpi=150)
print(f'Saved {args.out}')

#
# 4. The intervals of the chosen beats
#
table = report_h5.read_beat_table(args.h5).loc[closest]
print('\nMean intervals of the chosen beats (ms; 0 = not measured, left out)')
for col in ['rr', 'pr', 'qrs_duration', 'qt', 'qtc']:
    values = table[col].replace(0, np.nan).dropna()
    mean = f'{values.mean():.0f}' if len(values) else '-'
    print(f'  {col:<14}{mean:>5}  ({len(values)} of {len(table)} beats)')
