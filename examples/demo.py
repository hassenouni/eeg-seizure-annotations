"""Synthetic or local original-EEG algorithm demonstration."""

from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
from eeg_dataset_explorer.signals import synthetic, signal_array, sampling_rate
from eeg_annotations.intervals import segment, window_labels, Interval


def main() -> None:

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, help="Local NPZ with data and fs arrays")
    parser.add_argument("--figure", type=Path, help="Optional source signal plot (dataset explorer only)")
    args = parser.parse_args()
    if args.sample:
        with np.load(args.sample, allow_pickle=False) as sample:
            data = signal_array(sample["data"])
            fs = sampling_rate(float(sample["fs"]))
        source = "Original local EEG excerpt: " + args.sample.name
    else:
        fs = 256.0
        data = synthetic(fs)
        source = "Synthetic signal: not patient data"
    print(source)

    windows, starts = segment(data, fs, 2, 1)
    print("Complete windows:", windows.shape, "start times:", starts.tolist())
    if args.sample is None:
        labels = window_labels(starts, 2, [Interval(2, 4)])
        print("Explicitly synthetic interval labels:", labels.tolist())
    else:
        print("Real windows are not labeled: load dataset annotations before assigning labels.")


if __name__ == "__main__":
    main()
