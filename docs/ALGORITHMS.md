# Annotations and windows

`parse_chbmit(text)` parses file blocks and validates the stated seizure count.
`parse_siena(text)` converts clock boundaries relative to the recording start,
checking the recording duration and midnight rollover. It returns only files named
in the seizure list. Files absent from that list must not automatically be labeled
negative. Recordings lasting over 24 hours require date-aware interpretation.

`Interval(start, stop)` uses half-open seconds `[start, stop)`.
`segment(data, fs, seconds, stride)` returns full windows and their start times,
dropping incomplete tails. Window sizes are rounded to sample counts.
`window_labels` labels positive overlap or a specified minimum fraction of the
window. It rejects overlapping annotation intervals to prevent double counting.
Split by patient before making overlapping windows.
Text parsers do not yet decode CHB-MIT binary WFDB `.edf.seizures` files.

## References

- [Method or implementation reference](https://physionet.org/content/siena-scalp-eeg/1.0.0/)
- [CHB-MIT 1.0.0](https://physionet.org/content/chbmit/1.0.0/)
- [Siena 1.0.0](https://physionet.org/content/siena-scalp-eeg/1.0.0/)

## Real-data audit and CLI

```bash
python -m eeg_annotations YOUR_SUMMARY.txt --format chbmit
python -m eeg_annotations YOUR_SEIZURE_LIST.txt --format siena --recordings-root YOUR_SUBJECT_FOLDER
```

The CLI exits with code 2 when blocks need review or recording names are unresolved.
`audit_siena(text)` returns accepted events and explicit issues, whereas
`parse_siena(text)` fails strictly if any issue exists. It accepts shared recording
headers, abbreviated seizure clock fields, inherited registration clocks, mixed
colon/dot clock separators and whitespace inside an hour field.
It never chooses between multiple proposed clocks or silently renames a recording.

In the local Siena 1.0.0 text, three blocks need source review: PN00 seizure 3 ends
after its recording; PN10 seizure 2 lists alternative end times; PN10 seizure 3
lists clinical and electrical onset. Five recording names do not exactly match the
local EDF filenames (PN01, three PNO6 names, and PN11). Accepted text events are not
ready for labeling until these identities are reconciled. Rejected blocks must
never be converted to negative labels. Source annotations were left unchanged.
