import argparse
import pandas as pd


parser = argparse.ArgumentParser(
    description='Show the averages of the intervals.')
parser.add_argument('--intervals', type=str,
                    required=True,
                    help='path to intervals csv')

args = parser.parse_args()

df = pd.read_csv(args.intervals)
print(df.mean())
