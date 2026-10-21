"""Statistics from the beat table of an H5 report.

    python examples/beat_stats.py --h5 out/report.h5

Prints the recording summary, interval statistics over good-quality beats,
the breakdown by rhythm and beat class, and recomputes the HRV values to show
how they relate to the beat table.
"""
import argparse

import numpy as np
import pandas as pd

import report_h5

parser = argparse.ArgumentParser(description='Statistics from the beat table of an H5 report.')
parser.add_argument('--h5', type=str, required=True, help='path to report.h5')
args = parser.parse_args()

pd.set_option('display.width', 120)
pd.set_option('display.float_format', '{:.1f}'.format)

meta = report_h5.read_meta(args.h5)
config = report_h5.read_group_scalars(args.h5, 'config')
metrics = report_h5.read_group_scalars(args.h5, 'clinical_metrics')
beats = report_h5.read_beat_table(args.h5)

#
# Recording
#
hours = meta['analyzed_time_ms'] / 3_600_000
print(f'Report version     {meta["version"]} ({meta["version_date"]})')
print(f'Analyzed           {hours:.2f} h, {meta["leads"]} lead(s)')
if meta['start_time']:
    print(f'Start              {report_h5.clock_time(meta["start_time"], 0)}')
print(f'Beats              {len(beats)}')
print(f'Good-quality beats {beats["good_quality"].sum()} '
      f'({100 * beats["good_quality"].mean():.1f}%)')

#
# Intervals
#
# 0 means "not measured" for the interval columns (no P wave, no T wave, last
# beat, ...), so drop zeros per column. Only good-quality beats are used.
good = beats[beats['good_quality']]
columns = {
    'HR (bpm)': good['hr'],
    'RR (ms)': good['rr'],
    'P duration (ms)': good['p_duration'],
    'PR (ms)': good['pr'],
    'PR segment (ms)': good['pr_segment'],
    'QRS (ms)': good['qrs_duration'],
    'ST segment (ms)': good['st'],
    'QT (ms)': good['qt'],
    'QTc Bazett (ms)': good['qtc'],
}
rows = {}
for name, values in columns.items():
    values = values.astype(float).replace(0, np.nan).dropna()
    rows[name] = {
        'n': len(values),
        'mean': values.mean(),
        'std': values.std(),
        'p1': values.quantile(0.01),
        'median': values.median(),
        'p99': values.quantile(0.99),
    }
print('\nIntervals (good-quality beats, 0 / NaN dropped)')
print(pd.DataFrame(rows).T.astype({'n': int}))

#
# The report's own summary
#
# These use stricter samples (e.g. PR only from sinus beats inside
# config pr_min_ms..pr_max_ms), so they differ slightly from the table above.
print('\nClinical metrics stored in the report')
for key in ['average_hr_overall', 'pr_mean', 'qrs_mean', 'qtc_average',
            'hrv_sdnn', 'hrv_rmssd', 'hrv_pnn50', 'qtc_prolonged_episodes']:
    print(f'  {key:<24}{metrics[key]:.1f}')

#
# Rhythm and beat class
#
print('\nBeats by dominant rhythm')
by_rhythm = beats.groupby('dominant_rhythm').agg(
    beats=('hr', 'size'),
    mean_hr=('hr', 'mean'),
    mean_qrs=('qrs_duration', 'mean'),
)
by_rhythm['percent'] = 100 * by_rhythm['beats'] / len(beats)
print(by_rhythm)

print('\nBeats by class (pac_score / pvc_score >= 0.5)')
print(beats['beat_class'].value_counts().to_string())
print(f'Wide QRS (> 120 ms): {beats["qrs_wide"].sum()}')

#
# HRV from the beat table
#
# NN intervals: RR of beat i where beats i and i+1 are both normal sinus
# (not AF, beat class N), both good quality, and the RR is in range. The report
# uses a per-beat AF label that is not stored; dominant_rhythm stands in for it,
# so the values can differ around AF.
sinus = (beats['dominant_rhythm'] != 'AF') & (beats['beat_class'] == 'N') & beats['good_quality']
pair = sinus & sinus.shift(-1, fill_value=False)
rr = beats['rr'].astype(float)
nn = rr[pair & rr.between(config['rr_min_ms'], config['rr_max_ms'])].to_numpy()

if len(nn) >= 2:
    diff = np.diff(nn)
    print('\nHRV recomputed from the beat table (report value in brackets)')
    print(f'  SDNN   {nn.std():7.1f} ms  [{metrics["hrv_sdnn"]:.1f}]')
    print(f'  RMSSD  {np.sqrt(np.mean(diff ** 2)):7.1f} ms  [{metrics["hrv_rmssd"]:.1f}]')
    print(f'  pNN50  {100 * np.mean(np.abs(diff) > 50):7.1f} %   [{metrics["hrv_pnn50"]:.1f}]')
else:
    # The report's own HRV uses a per-beat AF label that is not stored in the
    # file, so it can still report HRV where dominant_rhythm is AF.
    print('\nHRV: fewer than two RR intervals between normal, non-AF beats in the beat table')
