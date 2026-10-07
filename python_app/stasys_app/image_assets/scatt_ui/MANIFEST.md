# STASYS UI assets (SCATT-derived pipeline)

Built by `tools/recreate_assets.py`. 36 files.

## Provenance
* `view/filter/favorites/ring_10/mark_*/dir_*` — carved from SCATT Basic's
  embedded resources and identified by their embedded Sketch `<title>` strings
  (e.g. `Icons/General/View`), then recoloured to the STASYS palette. All
  generic table/view geometry; no SCATT branding.
* `stasys_*` — ORIGINAL artwork created for the RECREATE slots listed in
  `docs/scatt_ui_spec.md` §7.1 (app icon, wordmark, session cards, device
  state, person, correction, calibration, direction arrows). Nothing from
  SCATT is copied here.

## Policy
No `scatt_*` resource ships in this directory. Uncarved/unattributed SCATT
SVGs remain under `scratch/scatt_extracted/assets/` for reference only.
