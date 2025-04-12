# 📦 Source Data Directory

This folder contains all raw and pre-processed data required to reproduce the analysis and figures.

These datasets are archived on Zenodo under the record:

🔗 https://zenodo.org/records/15192559

## 📥 How to populate this folder

To automatically download and extract the required archives, run:

```bash
invoke setup-source-data
```

This will:
- Download `ATLAS.zip` and extract it to `source_data/ATLAS/`
- Download `Data.zip` and extract it to `source_data/Data/`

## 📁 Expected Directory Structure

After setup, the contents of this folder should look like:

```
source_data/
├── ATLAS/
│   └── ...
├── Data/
│   └── ...
└── CONTENT.md
```

> Note: File names are illustrative. Actual structure and filenames depend on the archive contents.

## 🧠 Notes

- These archives are large. Ensure you have sufficient disk space before downloading.
- If the files already exist, `invoke` will not re-download or overwrite them.
