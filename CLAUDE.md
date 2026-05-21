# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

A PDF-to-structured-data pipeline for academic papers. It runs PDFs through [GROBID](https://github.com/kermitt2/grobid) to extract bibliographic metadata and full text, outputting TEI XML, JSON, and Markdown for each paper. Outputs are organized into subdirectories named by a per-paper hash extracted from the GROBID JSON (`biblio.hash`).

## Running the Pipeline

**Step 1 — Start GROBID** (requires Docker + NVIDIA GPU):
```bash
docker compose up -d
```
GROBID will be available at `http://localhost:8070`.

**Step 2 — Process PDFs:**
```bash
cd pdf2json
python pdf2tei-json-md.py                         # use default input/output dirs
python pdf2tei-json-md.py -i /path/to/pdfs -o /path/to/output
python pdf2tei-json-md.py -i ./input/pdfs -o ./output -s http://localhost:8070 -c 8 -v
```

**Utility — compute MD5 of a file:**
```bash
python scripts/md5_hash.py <file_path>
```

## Output Structure

```
pdf2json/output/
├── hash_index.json          # master index: hash → {files, biblio metadata}
├── <MD5_HASH>/
│   ├── paper.json           # structured metadata; biblio.hash drives directory name
│   ├── paper.grobid.tei.xml # raw GROBID TEI XML
│   └── paper.md             # Markdown version
└── unknown_N/               # papers where hash could not be extracted
```

## Key Data Flow

1. `GrobidClient.process()` sends all PDFs in the input directory to GROBID and writes flat output files (`.json`, `.grobid.tei.xml`, `.md`) into the output directory.
2. `organize_files_by_extracted_hash()` reads `biblio.hash` from each `.json`, creates a per-hash subdirectory, and moves the three output files into it.
3. `create_hash_index()` walks the output tree and writes `hash_index.json` with title, authors, DOI, and publication year for each entry.

## Dependencies

- Python: `grobid_client` (`pip install grobid-client-python`)
- Docker + NVIDIA Container Toolkit (for GPU-accelerated GROBID 0.9.0)
- GROBID image: `grobid/grobid:0.9.0-full`

## Ignored Paths

`*/output/` and `*/input/` are gitignored — processed results and source PDFs are not committed.
