import argparse
import os
import pyedflib
import numpy as np
import pandas as pd

from visualizer.ecg_to_pdf import ecg_to_pdf

parser = argparse.ArgumentParser(
    description='Create a PDF showing the output from the NeuralCloud Solutions API.')
parser.add_argument('--edf', type=str,
                    required=True,
                    help='path to edf')
parser.add_argument('--pqrst', type=str,
                    help='path to pqrst csv')
parser.add_argument('--max_pages', type=int,
                    default=1,
                    help='set the number of pages, use -1 for no limit')
parser.add_argument('--out', type=str,
                    default='out',
                    help='path to output folder')

args = parser.parse_args()


# Helper function to convert PQRST CSV to a Numpy array
def update_labels(label, onset, offset, sampling_rate, labels):
    # Check nans
    if np.isnan(onset) or np.isnan(offset):
        return

    # Convert miliseconds to location
    s = int(sampling_rate * onset / 1000.0)
    e = int(sampling_rate * offset / 1000.0)

    # Clip to prevent overflow
    s = np.clip(s, 0, labels.shape[0] - 1)
    e = np.clip(e, 0, labels.shape[0] - 1)

    # Set label for region
    labels[s:e] = label


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

# Load pqrst
labels = None
if args.pqrst:
    pqrst_df = pd.read_csv(args.pqrst)

    # Create label array
    labels = np.zeros((signal_length,), dtype=np.uint8)

    for _, row in pqrst_df.iterrows():
        p_on = row["ECG_P_Onsets"]
        p_off = row["ECG_P_Offsets"]

        qrs_on = row["ECG_R_Onsets"]
        qrs_off = row["ECG_R_Offsets"]

        t_on = row["ECG_T_Onsets"]
        t_off = row["ECG_T_Offsets"]

        update_labels(1, p_on, p_off, sampling_rate, labels)
        update_labels(2, qrs_on, qrs_off, sampling_rate, labels)
        update_labels(3, t_on, t_off, sampling_rate, labels)

# Save
ecg_to_pdf(
    sampling_rate=sampling_rate,
    output_path=os.path.join(args.out, 'tracings.pdf'),
    tracings=tracings,
    labels=labels,
    max_pages=args.max_pages
)
