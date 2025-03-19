# ECG Tutorials

This repository includes examples on how to analyize ECGs using NeuralCloud Solutions REST API.

An ECG is sent to the API as an EDF file. The file is then queued and processed. Once the analysis is done you can download the results.

#### Results

- P Wave Onset and Offset
- QRS Complex Onset and Offset
- T Wave Onset and Offset
- PR Interval
- RR Interval
- QT and QTc
- HR
- Duration of Waves and QRS Complex
- PR Segment and ST Segment

## Analyize EDF

### Setup

You will need to have Python installed and pip.

```
git clone https://github.com/NeuralCloudSolutions/ecg-tutorials.git
cd ecg-tutorials
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

You can also view the entire ECG. Note that this method might not be reasonable for large files.

```
python edf2pdf.py --edf example_output/original_ecg.edf --pqrst example_output/pqrst.csv --max_pages -1
```

### Stats

```
python calculate_averages.py --intervals example_output/intervals.csv
```

Output:

```
Heart Rate                99.227244
RR                       609.107335
P Wave Duration           67.192666
PR Segment                45.653085
PR Interval              112.845751
QRS Interval              70.949172
T Wave Duration          168.340982
ST Segment                73.928551
QT Interval              313.218705
QT Corrected (Bazett)    401.961588
```
