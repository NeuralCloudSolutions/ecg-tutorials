"""Analyze every EDF in a folder (recursively) in the cloud.

    python analyze_all_edfs.py --path path/to/edfs --out path/to/output
    python analyze_all_edfs.py --path path/to/edfs --out path/to/output --leads 1,2,3

Each EDF gets its own output folder, mirroring the input tree:
<out>/<relative path without .edf>/ holds a copy of the EDF and the job's
outputs (report.h5, report.pdf, tracings.pdf). A file that fails is reported
and skipped.
"""
import argparse
import os
import shutil

import requests

from analyze_edf import analyze, get_api_key, parse_leads

parser = argparse.ArgumentParser(description='Analyze every EDF in a folder.')
parser.add_argument('--path', type=str, required=True,
                    help='folder of EDFs (searched recursively), or a single EDF')
parser.add_argument('--out', type=str, default='out', help='output folder')
parser.add_argument('--leads', type=str, default='',
                    help='comma-separated 1-based leads to analyze in every file (default: all)')
args = parser.parse_args()

api_key = get_api_key()
leads = parse_leads(args.leads)


def get_edfs(path):
    if path.endswith('.edf'):
        yield path
        return

    for root, _, files in os.walk(path):
        for file in sorted(files):
            if file.endswith('.edf'):
                yield os.path.join(root, file)


failed = []
for edf_path in get_edfs(args.path):
    if os.path.isfile(args.path):
        relative = os.path.basename(edf_path)
    else:
        relative = os.path.relpath(edf_path, args.path)
    folder_path = os.path.join(args.out, relative[:-len('.edf')])
    os.makedirs(folder_path, exist_ok=True)

    print(f'\n{edf_path} -> {folder_path}')

    # Copy original to output
    shutil.copy2(edf_path, folder_path)

    try:
        analyze(edf_path, folder_path, api_key, leads)
    except (RuntimeError, requests.RequestException) as e:
        print(f'Error: {e}')
        failed.append(edf_path)

if failed:
    print(f'\n{len(failed)} file(s) failed:')
    for path in failed:
        print(f'  {path}')
