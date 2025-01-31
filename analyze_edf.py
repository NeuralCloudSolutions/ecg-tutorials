import requests
import time
import argparse
import os
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser(
    description='Analyze an EDF using the NeuralCloud Solutions API.')
parser.add_argument('--edf', type=str,
                    required=True,
                    help='path to edf')
parser.add_argument('--out', type=str,
                    default='out',
                    help='path to output folder')

args = parser.parse_args()

# Add your API key to the .env file
API_KEY = os.getenv('API_KEY')

# Upload ECG file
edf_file = args.edf

# Construct HTTP POST command
url = 'https://api.theneuralcloud.com/api/v1/ecg_wave_analysis'
headers = {'Authorization': f'Bearer {API_KEY}'}
files = {'file': open(edf_file, 'rb')}

# Send command to upload file
print(f'Sending file {edf_file}')
r = requests.post(url, files=files, headers=headers)

# Get response from server
data = r.json()

# Get job id
job_id = data['job']['id']

# Get job status (queued)
job_status = data['job']['status']

# Construct HTTP GET command to check status
url = f'https://api.theneuralcloud.com/api/v1/jobs/{job_id}'
headers = {'Authorization': f'Bearer {API_KEY}'}

# Run loop checking status
while not (job_status == 'completed' or
           job_status == 'error'):
    print(f'Current status {job_status}')

    # Sleep so we are not constantly calling the server
    time.sleep(5)

    # Get status
    r = requests.get(url, headers=headers)
    data = r.json()
    job_status = data['job']['status']

# Print the results
print(data)

# Save outputs
os.makedirs(args.out, exist_ok=True)

for output in data['job']['output_files']:

    # Get filname
    filename = output['filename']

    # Get url
    url = output['url']

    # Download the file
    r = requests.get(url, allow_redirects=True)

    # Write the file to disk
    open(os.path.join(args.out, filename), 'wb').write(r.content)
