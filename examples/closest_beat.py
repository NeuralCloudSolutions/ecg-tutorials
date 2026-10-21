"""Find the single beat closest to the record's average beat shape and plot it
with its onsets, offsets and peaks.

    python examples/closest_beat.py --h5 out/report.h5 --edf my.edf
    python examples/closest_beat.py --h5 out/report.h5 --edf my.edf --lead 2 --out out/closest_beat.png

The average shape is the centroid of the beat encodings (see
`report_h5.normal_centroid`), and the closest beat is the one with the highest
cosine similarity to it: a real beat that represents the record. The onsets
and offsets come from /beats and the peaks from /beat_peaks.

The H5 report has no tracings, so the EDF that was analyzed is needed. If the
analysis was run with --leads, pass the same --leads here.
"""
import argparse

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import report_h5

parser = argparse.ArgumentParser(description='Plot the beat closest to the average beat shape.')
parser.add_argument('--h5', type=str, required=True, help='path to report.h5')
parser.add_argument('--edf', type=str, required=True, help='path to the EDF that was analyzed')
parser.add_argument('--leads', type=str, default='',
                    help='the --leads the analysis was run with (default: all)')
parser.add_argument('--lead', type=int, default=1,
                    help='lead to use, 1-based position among the analyzed leads')
parser.add_argument('--out', type=str, default='out/closest_beat.png', help='output image')
args = parser.parse_args()

lead = args.lead - 1

#
# 1. The beat closest to the average shape
#
index, encoding = report_h5.encoded_beats(args.h5, lead)
centroid = report_h5.normal_centroid(encoding)
similarity = encoding @ centroid
best = int(index[np.argmax(similarity)])

beats = report_h5.read_beat_list(args.h5)
beat = beats[best]
print(f'Beat {best} at {beat.qrs.start / 1000:.2f} s, '
      f'cosine similarity {similarity.max():.4f} to the average shape')

#
# 2. Signal, in mV relative to the beat's baseline
#
signal, mv_per_unit = report_h5.load_lead(
    args.edf, report_h5.edf_lead(report_h5.parse_leads(args.leads), lead))
scale, unit = (mv_per_unit, 'mV') if np.isfinite(mv_per_unit) else (1.0, 'signal units')
baseline = report_h5.beat_baseline(signal, beat)


def trace(start_ms, end_ms):
    """(times in ms from the start of the recording, signal) over a span."""
    s = max(0, report_h5.ms_to_sample(start_ms))
    e = min(len(signal), report_h5.ms_to_sample(end_ms))
    t = np.arange(s, e) * 1000 / report_h5.SAMPLING_RATE
    return t, (signal[s:e] - baseline) * scale


def value_at(ms):
    return (signal[report_h5.ms_to_sample(ms)] - baseline) * scale


peaks = report_h5.read_beat_peaks(args.h5, lead)
peak_row = peaks.loc[best] if peaks is not None else None

fig, (ax_strip, ax) = plt.subplots(2, 1, figsize=(11, 8), height_ratios=[1, 2])

#
# 3. Context: a few seconds around the beat
#
t, y = trace(beat.qrs.start - 2500, beat.qrs.start + 2500)
ax_strip.plot(t / 1000, y, color='black', linewidth=0.8)
ax_strip.axvspan((beat.p.start if beat.p else beat.qrs.start) / 1000, beat.end / 1000,
                 color='gold', alpha=0.3)
ax_strip.set_xlabel('s')
ax_strip.set_ylabel(unit)
ax_strip.set_title(f'Beat {best}, lead {args.lead}, in context')

#
# 4. The beat with its onsets, offsets and peaks
#
# The x axis is ms from the QRS onset; the report's times are ms from the
# start of the recording, so subtract the onset when plotting.
onset = beat.qrs.start
start = (beat.p.start if beat.p else onset - 200) - 100
end = beat.end + 150
# Stop at the neighbouring beats
if best > 0:
    start = max(start, beats[best - 1].end)
if best + 1 < len(beats):
    end = min(end, beats[best + 1].qrs.start)
t, y = trace(start, end)
ax.plot(t - onset, y, color='black', linewidth=1.5)
ax.axhline(0, color='0.5', linewidth=0.5)

print('\nOnsets and offsets (ms from start of recording)')
waves = [('P', beat.p, 'tab:green'), ('QRS', beat.qrs, 'tab:red'), ('T', beat.t, 'tab:blue')]
for name, wave, color in waves:
    if wave is None:
        continue
    print(f'  {name:<4}{wave.start:>10} .. {wave.end}')
    ax.axvspan(wave.start - onset, wave.end - onset, color=color, alpha=0.12)
    for row, (x, label) in enumerate([(wave.start, f'{name} on'), (wave.end, f'{name} off')]):
        ax.axvline(x - onset, color=color, linestyle='--', linewidth=0.8)
        # Stagger on / off labels so neighbours do not overlap
        ax.annotate(label, (x - onset, 1.01 + 0.05 * row), xycoords=('data', 'axes fraction'),
                    ha='center', va='bottom', fontsize=8, color=color)

if peak_row is not None:
    markers = [('P', 'p', 'tab:green'), ('Q', 'q', 'tab:red'), ('R', 'r', 'tab:red'),
               ('S', 's', 'tab:red'), ("R'", 'r2', 'tab:red'),
               ('T', 't', 'tab:blue'), ('T2', 't', 'tab:blue')]
    for label, key, color in markers:
        pos_col, amp_col = (f'{key}_peak_ms', f'{key}_amp') if label != 'T2' else ('t_peak2_ms', 't_amp2')
        pos = int(peak_row[pos_col])
        if pos < 0:
            continue
        # The stored amplitude is in mV from the same baseline; fall back to
        # the trace when the EDF unit is unknown.
        amp = peak_row[amp_col] if np.isfinite(peak_row[amp_col]) and unit == 'mV' else value_at(pos)
        ax.plot(pos - onset, amp, 'o', color=color, markersize=7)
        ax.annotate(f'{label} {amp:.2f}', (pos - onset, amp), textcoords='offset points',
                    xytext=(8, 4 if amp >= 0 else -10), fontsize=9)
    ax.margins(y=0.12)
else:
    print('This report has no /beat_peaks group; plotting onsets and offsets only')

ax.set_xlabel(f'ms from QRS onset ({onset} ms from start of recording)')
ax.set_ylabel(f'{unit} from baseline')
ax.set_title('Onsets, offsets and peaks', pad=36)

fig.tight_layout()
fig.savefig(args.out, dpi=150)
print(f'Saved {args.out}')

#
# 5. The beat's measurements
#
row = report_h5.read_beat_table(args.h5).loc[best]
print('\nIntervals (ms)')
for col in ['rr', 'pr', 'qrs_duration', 'qt', 'qtc']:
    print(f'  {col:<14}{row[col]:.0f}')
print(f'  {"hr (bpm)":<14}{row["hr"]:.0f}')
if peak_row is not None:
    print('\nShape')
    print(f'  QRS {peak_row["qrs_shape"]}, T {peak_row["t_shape"]}, '
          f'ST at J+60 {peak_row["st_60"]:.3f} mV')
