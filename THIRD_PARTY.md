# Third-party data, software and licences

This project is independent and is not endorsed by any data provider.

## NHTSA ODI public data

Q1 uses the public flat files published by the National Highway Traffic Safety
Administration (NHTSA), Office of Defects Investigation:

| role | source |
|---|---|
| consumer complaints 2020-2024 | `https://static.nhtsa.gov/odi/ffdd/cmpl/COMPLAINTS_RECEIVED_2020-2024.zip` |
| consumer complaints 2025-2026 | `https://static.nhtsa.gov/odi/ffdd/cmpl/COMPLAINTS_RECEIVED_2025-2026.zip` |
| recalls since 2010 | `https://static.nhtsa.gov/odi/ffdd/rcl/FLAT_RCL_POST_2010.zip` |
| defect investigations | `https://static.nhtsa.gov/odi/ffdd/inv/FLAT_INV.zip` |
| manufacturer communications (optional, recorded but not derived) | `https://static.nhtsa.gov/odi/ffdd/tsbs/TSBS_RECEIVED_2020-2024.zip`, `https://static.nhtsa.gov/odi/ffdd/tsbs/TSBS_RECEIVED_2025-2026.zip` |

File layouts: `cmpl/CMPL.txt`, `rcl/RCL.txt`, `inv/INV.txt` and
`tsbs/TSBS.txt` under the same host.

### Public-domain statement

NHTSA's Terms of Use, section **Ownership**, states:

> "Information presented on this web site is considered public information and
> may be distributed or copied."

— National Highway Traffic Safety Administration, *Terms of Use*,
<https://www.nhtsa.gov/node/32151>, accessed 2026-10-31.

The same status follows from the federal-copyright rule: 17 U.S.C. §105
provides that copyright protection is not available for any work of the United
States Government. The NHTSA files are therefore public information. NHTSA/DOT
does not endorse this project, and the downloaded data is provided without any
warranty of accuracy or fitness (the Terms of Use disclaim such warranties).

### What this project stores

- Raw downloads stay under the git-ignored `data/raw/` directory.
- `data/SNAPSHOT.json` records each download's URL, sha256, size,
  `Last-Modified` header and download time.
- The committed files under `data/` are derived, de-identified selections:
  location and identity columns are dropped, and complaint narratives that
  match the PII screen are removed. `data/STATS.md` records the counts.

All other software licences are recorded here as later lanes add dependencies.
The project itself is MIT licensed; see `LICENSE`.
