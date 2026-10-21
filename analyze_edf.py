"""Analyze an EDF in the cloud and download the H5 report.

    python analyze_edf.py --edf example_files/mitdb_221_60s.edf --out out
    python analyze_edf.py --edf my.edf --leads 1,2,3

The job produces:

    report.h5      the full analysis (beats, beat table, events, beat encodings, ...)
    report.pdf     a summary report
    tracings.pdf   up to 10 pages of tracings with the P, QRS and T labels

The PDFs are best effort: a job can complete with only report.h5.
"""
import argparse
import hashlib
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

API_URL = 'https://api.theneuralcloud.com/api/v1'


def calculate_md5(file_path):
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b''):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def get_api_key():
    """The API key from .env, or exit with instructions."""
    load_dotenv()
    api_key = os.getenv('API_KEY')
    if not api_key or not api_key.strip():
        sys.exit('Error: No API_KEY found. Please create a file called .env and add the API key. '
                 'See .env.sample for an example.')
    return api_key


def parse_leads(text):
    """'1,2,3' -> [1, 2, 3]; '' -> None (every lead)."""
    return [int(x) for x in text.split(',') if x.strip()] or None


def analyze(edf_path, out_dir, api_key, leads=None):
    """Run the analysis on `edf_path` and download its outputs into `out_dir`.

    `leads` is a list of 1-based EDF signal numbers to analyze (None for every
    lead). Returns the path of the downloaded report.h5. Raises RuntimeError
    when a step fails.
    """
    auth = {'Authorization': f'Bearer {api_key}'}

    #
    # Step 1: Create an API File
    #
    print(f'Creating an API File for {edf_path}')
    response = requests.post(f'{API_URL}/files',
                             headers=auth,
                             json={'byte_size': os.path.getsize(edf_path),
                                   'md5sum': calculate_md5(edf_path)})
    if response.status_code != 200:
        raise RuntimeError(f'Failed to create the API File: {response.content}')
    file = response.json()['file']
    print(f'Created a new API File with ID: {file["id"]}')

    #
    # Step 2: Upload the file
    #
    print('Uploading the file')
    with open(edf_path, 'rb') as f:
        upload = requests.put(file['upload']['url'],
                              headers=file['upload']['headers'],
                              data=f)
    if upload.status_code != 200:
        raise RuntimeError(f'Failed to upload the file. Status code: {upload.status_code}')

    #
    # Step 3: Confirm the file was uploaded
    #
    confirmation = requests.post(file['upload']['confirmation_url'], headers=auth)
    status = confirmation.json()['file']['status']
    if status != 'confirmed':
        raise RuntimeError(f'File upload confirmation failed (status {status!r})')
    print('Upload confirmed')

    #
    # Step 4: Create the job
    #
    payload = {'file_id': file['id']}
    if leads:
        payload['leads'] = leads
        print(f'Only analyzing leads: {leads}')

    response = requests.post(f'{API_URL}/ecg_wave_analysis', headers=auth, json=payload)
    if response.status_code != 201:
        raise RuntimeError(f'Failed to launch the job: {response.content}')

    job = response.json()['job']
    print(f'Launched job {job["id"]} (status {job["status"]!r})')

    #
    # Step 5: Wait for the job to finish
    #
    while job['status'] not in ('completed', 'error'):
        # Sleep so we are not constantly calling the server
        time.sleep(5)
        job = requests.get(f'{API_URL}/jobs/{job["id"]}', headers=auth).json()['job']
        print(f'Current job status: {job["status"]}')

    if job['status'] != 'completed':
        print(json.dumps(job, indent=2))
        raise RuntimeError(f'Job failed: {job.get("error")}')

    #
    # Step 6: Download the outputs
    #
    os.makedirs(out_dir, exist_ok=True)
    report_path = None
    for output in job.get('output_files', []):
        output_path = os.path.join(out_dir, output['filename'])
        print(f'Downloading {output["filename"]} to {output_path}')

        r = requests.get(output['url'], allow_redirects=True)
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            f.write(r.content)

        if output['filename'].endswith('.h5'):
            report_path = output_path

    if report_path is None:
        raise RuntimeError('The job completed without an H5 report')
    return report_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Analyze an EDF using the NeuralCloud Solutions API and download the H5 report.')
    parser.add_argument('--edf', type=str, required=True, help='path to the EDF')
    parser.add_argument('--out', type=str, default='out', help='output folder')
    parser.add_argument('--leads', type=str, default='',
                        help='comma-separated 1-based leads to analyze (default: all)')
    args = parser.parse_args()

    try:
        report_path = analyze(args.edf, args.out, get_api_key(), parse_leads(args.leads))
    except (RuntimeError, requests.RequestException) as e:
        sys.exit(f'Error: {e}')

    print(f'\nH5 report: {report_path}')
