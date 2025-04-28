import argparse
import requests
import time
import os
import numpy as np
import pyedflib
import shutil
import hashlib
import json
from dotenv import load_dotenv

from visualizer.ecg_to_pdf import Region, ecg_to_pdf
from visualizer.report import report

load_dotenv()

parser = argparse.ArgumentParser(
    description='Run all EDFs.')
parser.add_argument('--path', type=str,
                    required=True,
                    help='path to EDFs')
parser.add_argument('--max_pages', type=int,
                    default=1,
                    help='set the number of pages, use -1 for no limit')
parser.add_argument('--out', type=str,
                    default='out',
                    help='path to output folder')

args = parser.parse_args()

# Add your API key to the .env file
API_KEY = os.getenv('API_KEY')

if args.path[-1] != '/':
    args.path += '/'

if args.out[-1] != '/':
    args.out += '/'


def get_edfs(path):
    if path.endswith('.edf'):
        return [path]

    for file in os.listdir(path):
        if file == 'analysis':
            continue
        filepath = os.path.join(path, file)
        if file.endswith('.edf'):
            yield filepath

        elif os.path.isdir(filepath):
            os.makedirs(filepath.replace(
                args.path, args.out), exist_ok=True)
            yield from get_edfs(filepath)


# Calculate MD5 hash
def calculate_md5(file_path):
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b''):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def analyze(edf_file, out_path):
    file_size = os.path.getsize(edf_file)
    md5sum = calculate_md5(edf_file)

    #
    # Step 1: Create an API File
    #
    print(f'Creating an API File for {edf_file}')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    }
    payload = {
        'byte_size': file_size,
        'md5sum': md5sum
    }

    response = requests.post('https://api.theneuralcloud.com/api/v1/files',
                             headers=headers,
                             data=json.dumps(payload))
    print(response)
    data = response.json()

    upload_url = data['file']['upload']['url']
    file_id = data['file']['id']
    confirmation_url = data['file']['upload']['confirmation_url']
    upload_headers = data['file']['upload']['headers']

    print(f'Created a new API File with ID: {file_id}')

    #
    # Step 2: Upload the file
    #
    print(f'Uploading file to {upload_url}')
    upload_response = requests.put(upload_url,
                                   headers=upload_headers,
                                   data=open(edf_file, 'rb'))

    if upload_response.status_code != 200:
        print(
            f'Failed to upload the file. Status code: {upload_response.status_code}')
        exit(1)

    print('Uploaded the file successfully')

    #
    # Step 3: Confirm the file was uploaded
    #
    print('Confirming the file was uploaded')
    confirmation_response = requests.post(confirmation_url,
                                          headers={'Authorization': f'Bearer {API_KEY}'})
    confirmation_data = confirmation_response.json()
    file_status = confirmation_data['file']['status']

    print(f'API File status: {file_status}')
    if file_status != 'confirmed':
        print('File upload confirmation failed')
        exit(1)

    #
    # Step 4: Create the job
    #
    print('Launching the job')
    job_payload = {
        'file_id': file_id
    }
    job_response = requests.post('https://api.theneuralcloud.com/api/v1/ecg_wave_analysis',
                                 headers={
                                     'Content-Type': 'application/json',
                                     'Authorization': f'Bearer {API_KEY}'
                                 },
                                 data=json.dumps(job_payload))
    job_data = job_response.json()
    job_id = job_data['job']['id']
    job_status = job_data['job']['status']

    print(f'Launched a new job with ID {job_id} (status \'{job_status}\')')

    if job_response.status_code != 201:
        print('Failed to launch the job')
        exit(1)

    # Check job status until completion
    url = f'https://api.theneuralcloud.com/api/v1/jobs/{job_id}'
    headers = {'Authorization': f'Bearer {API_KEY}'}

    while not (job_status == 'completed' or job_status == 'error'):
        print(f'Current job status: {job_status}')

        # Sleep so we are not constantly calling the server
        time.sleep(5)

        # Get status
        r = requests.get(url, headers=headers)
        data = r.json()
        job_status = data['job']['status']

    # Print the results
    print('Job completed with status:', job_status)
    print(json.dumps(data, indent=2))

    # Save outputs
    if job_status == 'completed' and 'output_files' in data['job']:
        os.makedirs(out_path, exist_ok=True)

        for output in data['job']['output_files']:
            # Get filename
            filename = output['filename']

            # Get url
            url = output['url']

            print(f'Downloading {filename}')

            # Download the file
            r = requests.get(url, allow_redirects=True)

            # Write the file to disk
            output_path = os.path.join(out_path, filename)
            with open(output_path, 'wb') as f:
                f.write(r.content)

            print(f'Saved to {output_path}')
    else:
        print('No output files to download or job failed')


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


def save_tracing(edf_path, json_data, output_path):
    # Load EDF
    edf_file = pyedflib.EdfReader(edf_path)

    n_leads = len(edf_file.getNSamples())
    signal_length = edf_file.getNSamples()[0]
    tracings = np.empty((n_leads, signal_length))
    for i in range(n_leads):
        sampling_rate = edf_file.getSampleFrequencies()[i]
        tracing = edf_file.readSignal(i)
        tracings[i, :] = tracing

    # Create label array
    labels = np.zeros((signal_length,), dtype=np.uint8)

    for beat in json_data['beats']:
        p_waves = beat['p']

        for p in p_waves:
            update_labels(1, p['s'], p['e'], sampling_rate, labels)

        update_labels(2, beat['qrs']['s'], beat['qrs']
                      ['e'], sampling_rate, labels)

        if 't' in beat:
            t_on = beat['t']['s']
            t_off = beat['t']['e']
            update_labels(3, t_on, t_off, sampling_rate, labels)

    # Save
    ecg_to_pdf(
        sampling_rate=sampling_rate,
        output_path=output_path,
        tracings=tracings,
        labels=labels,
        max_pages=args.max_pages
    )


# Save outputs
os.makedirs(args.out, exist_ok=True)


for edf_path in get_edfs(args.path):
    folder_path = edf_path.replace(args.path, args.out)[:-4] + '/'
    os.makedirs(folder_path, exist_ok=True)

    print(f'{edf_path} - {folder_path}')

    # Copy orignal to output
    shutil.copy2(edf_path, folder_path)

    # Analyze file
    analyze(edf_path, folder_path)

    print('Loading JSON ...')
    with open(os.path.join(folder_path, 'analysis.json')) as f:
        d = json.load(f)

        save_tracing(edf_path, d, os.path.join(folder_path, 'tracing.pdf'))
        save_tracing(os.path.join(folder_path, 'ecg.edf'), d,
                     os.path.join(folder_path, 'clean_tracing.pdf'))

        # Load EDF
        edf_file = pyedflib.EdfReader(edf_path)

        n_leads = len(edf_file.getNSamples())
        signal_length = edf_file.getNSamples()[0]
        tracings = np.empty((n_leads, signal_length))
        for i in range(n_leads):
            sampling_rate = edf_file.getSampleFrequencies()[i]
            tracing = edf_file.readSignal(i)
            tracings[i, :] = tracing

        # Save
        print('Saving Report ...')
        report(
            tracings,
            sampling_rate,
            d,
            os.path.join(folder_path, 'report.pdf')
        )

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
            output_path=os.path.join(folder_path, 'events.pdf'),
            tracings=tracings,
            regions=regions,
            max_pages=args.max_pages
        )
