"""Convert the H5 beat list into Python objects.

    python examples/beat_list.py --h5 out/report.h5

Each beat becomes a `Beat` with its QRS complex, its P waves (zero or more)
and its T wave (or None). Every wave is a `Wave(start, end)` in ms from the
start of the recording. See `read_beat_list` in report_h5.py for the
conversion.
"""
import argparse

import report_h5

parser = argparse.ArgumentParser(description='Read the beat list from an H5 report.')
parser.add_argument('--h5', type=str, required=True, help='path to report.h5')
parser.add_argument('--show', type=int, default=5, help='number of beats to print')
args = parser.parse_args()

beats = report_h5.read_beat_list(args.h5)

print(f'{len(beats)} beats\n')
for beat in beats[:args.show]:
    print(beat)

# Working with the objects
with_p = sum(1 for b in beats if b.p_waves)
multiple_p = sum(1 for b in beats if len(b.p_waves) > 1)
without_t = sum(1 for b in beats if b.t is None)

print()
print(f'Beats with a P wave:            {with_p}')
print(f'Beats with more than one P:     {multiple_p}')
print(f'Beats without a T wave:         {without_t}')

# Intervals computed directly from the objects
beat = next(b for b in beats if b.p is not None and b.t is not None)
print()
print(f'Beat {beat.index}:')
print(f'  P duration   {beat.p.duration} ms')
print(f'  PR interval  {beat.qrs.start - beat.p.start} ms')
print(f'  QRS duration {beat.qrs.duration} ms')
print(f'  QT interval  {beat.t.end - beat.qrs.start} ms')
