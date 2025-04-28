import argparse
import os
import pyedflib
import numpy as np
import json

from visualizer.ecg_to_pdf import Region, ecg_to_pdf

parser = argparse.ArgumentParser(
    description='Create a PDF showing the events detected from the NeuralCloud Solutions API.')
parser.add_argument('--edf', type=str,
                    required=True,
                    help='path to edf')
parser.add_argument('--json', type=str,
                    required=True,
                    help='path to json')
parser.add_argument('--max_pages', type=int,
                    default=1,
                    help='set the number of pages, use -1 for no limit')
parser.add_argument('--out', type=str,
                    default='out',
                    help='path to output folder')

args = parser.parse_args()


# Save outputs
os.makedirs(args.out, exist_ok=True)

# Load EDF
edf_file = pyedflib.EdfReader(args.edf)

n_leads = len(edf_file.getNSamples())
signal_length = edf_file.getNSamples()[0]
tracings = np.empty((n_leads, signal_length))
for i in range(n_leads):
    sampling_rate = edf_file.getSampleFrequencies()[i]
    tracing = edf_file.readSignal(i)
    tracings[i, :] = tracing

print("Loading JSON ...")
with open(args.json) as f:
    d = json.load(f)

    regions = []

    events = d['events']

    afib_events = events['afib']
    pac_events = events['pac']
    pvc_events = events['pvc']
    av_block_events = events['av_block']
    pause_events = events['pauses']

    for event in afib_events:
        regions.append(
            Region(
                event['s'],
                event['e'],
                color='red'
            ))

    for event in pac_events:
        regions.append(
            Region(
                event['s'],
                event['e'],
                color='yellow'
            ))

    for event in pvc_events:
        regions.append(
            Region(
                event['s'],
                event['e'],
                color='orange'
            ))

    for event in av_block_events:
        regions.append(
            Region(
                event['s'],
                event['e'],
                color='green'
            ))

    for event in pause_events:
        regions.append(
            Region(
                event['s'],
                event['e'],
                color='blue'
            ))

    # Save
    print('Saving Events ...')
    ecg_to_pdf(
        sampling_rate=sampling_rate,
        output_path=os.path.join(args.out, 'events.pdf'),
        tracings=tracings,
        regions=regions,
        max_pages=args.max_pages
    )
