import requests
import time
import argparse
import os
import hashlib
import json
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

# File information
edf_file = args.edf
file_size = os.path.getsize(edf_file)

# Calculate MD5 hash
def calculate_md5(file_path):
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b''):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

md5sum = calculate_md5(edf_file)

#
# Step 1: Create an API File
#
print(f"Creating an API File for {edf_file}")
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
data = response.json()

upload_url = data['file']['upload']['url']
file_id = data['file']['id']
confirmation_url = data['file']['upload']['confirmation_url']
upload_headers = data['file']['upload']['headers']

print(f"Created a new API File with ID: {file_id}")

#
# Step 2: Upload the file
#
print(f"Uploading file to {upload_url}")
upload_response = requests.put(upload_url,
                              headers=upload_headers,
                              data=open(edf_file, 'rb'))

if upload_response.status_code != 200:
    print(f"Failed to upload the file. Status code: {upload_response.status_code}")
    exit(1)

print("Uploaded the file successfully")

#
# Step 3: Confirm the file was uploaded
#
print("Confirming the file was uploaded")
confirmation_response = requests.post(confirmation_url,
                                     headers={'Authorization': f'Bearer {API_KEY}'})
confirmation_data = confirmation_response.json()
file_status = confirmation_data['file']['status']

print(f"API File status: {file_status}")
if file_status != 'confirmed':
    print("File upload confirmation failed")
    exit(1)

#
# Step 4: Create the job
#
print("Launching the job")
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

print(f"Launched a new job with ID {job_id} (status '{job_status}')")

if job_response.status_code != 201:
    print("Failed to launch the job")
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
print("Job completed with status:", job_status)
print(json.dumps(data, indent=2))

# Save outputs
if job_status == 'completed' and 'output_files' in data['job']:
    os.makedirs(args.out, exist_ok=True)

    for output in data['job']['output_files']:
        # Get filename
        filename = output['filename']

        # Get url
        url = output['url']

        print(f"Downloading {filename}")

        # Download the file
        r = requests.get(url, allow_redirects=True)

        # Write the file to disk
        output_path = os.path.join(args.out, filename)
        with open(output_path, 'wb') as f:
            f.write(r.content)

        print(f"Saved to {output_path}")
else:
    print("No output files to download or job failed")
