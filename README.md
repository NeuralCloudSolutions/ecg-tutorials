# ECG Scripts

## Analyize and EDF

### Setup

You will need to have Python installed and pip.

```
git clone https://github.com/NeuralCloudSolutions/ecg-scripts.git
cd ecg-scripts
pip install -r requirements.txt
```

Next you will need to create an account on NeuralCloud.

1. Go to https://app.theneuralcloud.com
2. Sign up
3. You will then receive an email and you will need to confirm your email
4. Sign in and go to the billings page
5. Select a plan and enter your billing information
6. Go to "API Keys" and create a new API Key
7. Save the key in .env (see .env.sample)

### Running Analysis

```
python analyze_edf.py --edf example_output/original_ecg.edf
```

By default the files from the analysis will be saved in the folder `out`. You can change the output path using the following:

```
python analyze_edf.py --edf example_output/original_ecg.edf --out my_output_folder
```

### Visualize

You can create a PDF showing the PQRST labeling.

```
python edf2pdf.py --edf example_output/original_ecg.edf --pqrst example_output/pqrst.csv
```
