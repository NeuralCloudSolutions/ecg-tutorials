"""Write the event tables of an H5 report to CSV.

    python examples/events_to_csv.py --h5 out/report.h5 --out out/events

Writes one CSV per table:

    rhythm_events.csv     NSR, sinus tach / brady, AF and indeterminate episodes
    ectopic_events.csv    PAC / PVC singles, couplets, triplets and runs
    gap_events.csv        pauses
    artifact_events.csv   low signal quality regions, per lead

Times are ms from the start of the recording. When the recording has a start
time, `start_clock` / `end_clock` columns give the wall-clock time too.
See docs/EVENTS.md for every column.
"""
import argparse
import os

import report_h5

parser = argparse.ArgumentParser(description='Write the event tables of an H5 report to CSV.')
parser.add_argument('--h5', type=str, required=True, help='path to report.h5')
parser.add_argument('--out', type=str, default='out/events', help='output folder')
args = parser.parse_args()

os.makedirs(args.out, exist_ok=True)

start_time = report_h5.read_meta(args.h5)['start_time']
events = report_h5.read_events(args.h5)

# The artifact table names its columns start / end; match the other tables
events['artifact'] = events['artifact'].rename(columns={'start': 'start_ms', 'end': 'end_ms'})
events['artifact']['duration_ms'] = events['artifact']['end_ms'] - events['artifact']['start_ms']

# Leading columns per table; the rest keep their order
first = {
    'rhythm': ['id', 'type', 'start_ms', 'end_ms', 'duration_ms', 'start_beat', 'end_beat',
               'beat_count', 'confidence', 'hr_mean', 'hr_min', 'hr_max'],
    'ectopic': ['id', 'type', 'kind', 'start_ms', 'end_ms', 'duration_ms', 'start_beat',
                'end_beat', 'beat_count', 'confidence'],
    'gap': ['id', 'type', 'start_ms', 'end_ms', 'duration_ms', 'before_beat', 'after_beat',
            'confidence'],
    'artifact': ['lead', 'start_ms', 'end_ms', 'duration_ms', 'quality'],
}

for name, df in events.items():
    df = df[first[name] + [c for c in df.columns if c not in first[name]]]

    if start_time:
        df.insert(df.columns.get_loc('end_ms') + 1, 'start_clock',
                  report_h5.clock_time(start_time, df['start_ms']))
        df.insert(df.columns.get_loc('start_clock') + 1, 'end_clock',
                  report_h5.clock_time(start_time, df['end_ms']))

    path = os.path.join(args.out, f'{name}_events.csv')
    df.to_csv(path, index=False)
    print(f'{len(df):6d} {name} events -> {path}')
