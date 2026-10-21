"""Write the beat table of an H5 report to CSV, one row per beat.

    python examples/beat_table_to_csv.py --h5 out/report.h5 --out out/beats.csv
    python examples/beat_table_to_csv.py --h5 out/report.h5 --out out/beats.csv --peaks

The CSV has the wave onsets and offsets, the intervals, heart rate, quality,
beat class, rhythm scores and flags. Missing values (no P wave, no T wave)
are empty cells. With --peaks, the per-lead P, Q, R, S and T peaks are added
as `lead<n>_<column>` columns. See docs/BEAT_TABLE.md for every column.
"""
import argparse
import os

import pandas as pd

import report_h5

parser = argparse.ArgumentParser(description='Write the beat table of an H5 report to CSV.')
parser.add_argument('--h5', type=str, required=True, help='path to report.h5')
parser.add_argument('--out', type=str, default='out/beats.csv', help='output CSV')
parser.add_argument('--peaks', action='store_true',
                    help='add the per-lead peak positions and amplitudes from /beat_peaks')
args = parser.parse_args()

beats = report_h5.read_beat_table(args.h5)

start_time = report_h5.read_meta(args.h5)['start_time']
if start_time:
    beats.insert(0, 'clock', report_h5.clock_time(start_time, beats['qrs_onset_ms']))

if args.peaks:
    n_leads = report_h5.read_meta(args.h5)['leads']
    peaks = [report_h5.read_beat_peaks(args.h5, lead) for lead in range(n_leads)]
    if peaks[0] is None:
        print('This report has no /beat_peaks group; writing the beat table only')
    else:
        beats = pd.concat([beats] + [p.add_prefix(f'lead{lead + 1}_')
                                     for lead, p in enumerate(peaks)], axis=1)

os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
beats.to_csv(args.out)
print(f'{len(beats)} beats x {beats.shape[1]} columns -> {args.out}')
