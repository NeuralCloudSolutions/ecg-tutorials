import argparse
import os
import pyedflib
import numpy as np
import json

from visualizer.report import report

parser = argparse.ArgumentParser(
    description='Create a PDF showing the report detected from the NeuralCloud Solutions API.')
parser.add_argument('--edf', type=str,
                    required=True,
                    help='path to edf')
parser.add_argument('--json', type=str,
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

    # Save
    print('Saving Report ...')
    report(
        tracings,
        sampling_rate,
        d,
        os.path.join(args.out, "report.pdf")
    )
