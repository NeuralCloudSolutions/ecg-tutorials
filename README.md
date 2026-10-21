# ECG Tutorials

This repository shows how to analyze ECGs with the NeuralCloud Solutions REST API and work with the
results.

You send an ECG to the API as an EDF file. It is queued and analyzed, and when the analysis is done
you download the results as an H5 report file. The report holds:

- every beat, with its P wave, QRS complex and T wave onsets and offsets
- per-beat intervals (RR, PR, QRS, QT, QTc, ST and PR segments), heart rate and signal quality
- per-beat PAC / PVC and rhythm scores
- P, Q, R, S and T peak positions and amplitudes, ST levels, and QRS and T shapes, per lead
- a beat encoding: a 16-number description of each beat's shape, per lead
- rhythm events (NSR, sinus tachycardia / bradycardia, AF / flutter), PAC / PVC events, pauses
  and low-quality regions
- summary metrics: average heart rate, HRV, interval summaries, histograms and hourly statistics

The job also returns two PDFs: a summary report and labeled tracings.

## Setup

You will need Python and pip.

```
git clone https://github.com/NeuralCloudSolutions/ecg-tutorials.git
cd ecg-tutorials
pip install -r requirements.txt
```

Next, create an account on NeuralCloud:

1. Go to https://app.theneuralcloud.com
2. Sign up
3. Confirm your email address from the email you receive
4. Sign in and go to the billing page
5. Select a plan and enter your billing information
6. Go to "API Keys" and create a new API key
7. Save the key in `.env` (see `.env.sample`)

## Running the analysis

```
python analyze_edf.py --edf example_files/mitdb_100_60s.edf
```

The outputs are saved to `out/` (`report.h5`, `report.pdf`, `tracings.pdf`). Use `--out` to pick
another folder.

We support up to 12-lead ECGs. To analyze only some leads, list them (1-based):

```
python analyze_edf.py --edf my.edf --leads 1,2,3
```

### Batch run

To analyze every EDF in a folder (including sub-folders):

```
python analyze_all_edfs.py --path path/to/input/edfs --out path/to/output/dir
```

Each EDF gets its own output folder, mirroring the input folders. `--leads` works here too and is
applied to every file. A file that fails is reported and skipped.

## Working with the H5 report

[docs/FORMAT.md](docs/FORMAT.md) describes the file. The scripts in [examples/](examples/) show how to use
it, and all run on the example reports in `example_files/`:

| Script | What it shows |
| --- | --- |
| [examples/beat_list.py](examples/beat_list.py) | Convert the H5 beat list into Python objects |
| [examples/beat_stats.py](examples/beat_stats.py) | Statistics on the beat table: intervals, rhythm, beat classes, HRV |
| [examples/beat_table_to_csv.py](examples/beat_table_to_csv.py) | Write the beat table to CSV (`--peaks` adds the per-lead peaks) |
| [examples/events_to_csv.py](examples/events_to_csv.py) | Write the rhythm, ectopic, pause and artifact events to CSV |
| [examples/normal_beat.py](examples/normal_beat.py) | Find the normal beat with the beat encodings: average the 50 most typical beats |
| [examples/closest_beat.py](examples/closest_beat.py) | Find the most typical single beat and plot its onsets, offsets and peaks |
| [examples/report_h5.py](examples/report_h5.py) | The reading helpers the scripts share |

```
python examples/beat_list.py --h5 example_files/mitdb_100_60s_report.h5
python examples/beat_stats.py --h5 example_files/mitdb_100_60s_report.h5
python examples/beat_table_to_csv.py --h5 example_files/mitdb_100_60s_report.h5 --out out/beats.csv --peaks
python examples/events_to_csv.py --h5 example_files/mitdb_221_60s_report.h5 --out out/events
python examples/normal_beat.py --h5 example_files/mitdb_100_60s_report.h5 --edf example_files/mitdb_100_60s.edf --out out/normal_beat.png
python examples/closest_beat.py --h5 example_files/mitdb_100_60s_report.h5 --edf example_files/mitdb_100_60s.edf --out out/closest_beat.png
```

The results of every script on both example reports are in
[example_outputs/](example_outputs/), one folder per record: the printed output (`.txt`), the CSVs
and the plots.

The report contains no signal, so the two plotting scripts also need the EDF that was analyzed. If
you analyzed with `--leads`, pass the same `--leads` to them, and pick the lead to plot with `--lead`
(1-based, among the analyzed leads).

Reference docs:

- [docs/BEAT_TABLE.md](docs/BEAT_TABLE.md): the beats, the beat table and the per-lead peaks
- [docs/EVENTS.md](docs/EVENTS.md): the event tables
- [docs/BEAT_ENCODING.md](docs/BEAT_ENCODING.md): the beat encoding and how to compare beat shapes

## Example data

`example_files/` has the first 60 seconds of two records of the
[MIT-BIH Arrhythmia Database](https://physionet.org/content/mitdb/1.0.0/) (2 leads, 360 Hz), each
with its analysis:

| EDF | Report | Record |
| --- | --- | --- |
| `mitdb_100_60s.edf` | `mitdb_100_60s_report.h5` | Normal sinus rhythm with 2 PACs |
| `mitdb_221_60s.edf` | `mitdb_221_60s_report.h5` | Atrial fibrillation with 12 PVCs |

> Moody GB, Mark RG. The impact of the MIT-BIH Arrhythmia Database. IEEE Eng in Med and Biol
> 20(3):45-50 (May-June 2001). Goldberger A, et al. PhysioBank, PhysioToolkit, and PhysioNet.
> Circulation 101(23):e215-e220 (2000).
