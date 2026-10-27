# BR/ACC Data Source Catalog


The source registry is the inventory of implemented pipelines and discovered data
sources. It is not a measurement of the database running on this machine.
Existing load states are retained from the reference registry; this catalog update
did not download datasets or validate a Neo4j load. Production reference counters
and their timestamp are documented separately in [Reference Metrics](reference_metrics.md).

## Registry

- [Source registry CSV](source_registry_br_v1.csv): source IDs, canonical URLs,
  implementation and load states, ownership, and catalog references.
- [Pipeline status](pipeline_status.md): generated input contracts and readiness.
- [Brazil Visible metadata snapshot](catalogs/brazil_visible.json): authentication,
  formats, linking fields, tags, related sources, and reported URL health.

The generated summary covers sources with `in_universe_v1=true`.

<!-- SOURCE_SUMMARY_START -->
**Generated from `docs/source_registry_br_v1.csv` (as-of UTC: 2026-10-27T02:20:27Z)**

- Universe v1 sources: 168
- Implemented pipelines: 47
- Loaded sources (load_state=loaded): 36
- Partial sources (load_state=partial): 8
- Not loaded sources (load_state=not_loaded): 124
- Status counts: loaded=36, partial=7, stale=3, blocked_external=1, not_built=121
<!-- SOURCE_SUMMARY_END -->

## Brazil Visible catalog update

On 2026-10-26, metadata from **92 documentation pages in 22 categories** was
imported from [Brazil Visible](https://github.com/nferdica/brazil-visible), pinned
to revision `cad147d28695d2faaa01fa0667ae53b7fef5e776`.

- **31 pages map to 25 existing source IDs.** Multiple pages can describe one
  local pipeline: CNPJ includes company, establishment and QSA documentation;
  CEIS/CNEP share the sanctions pipeline; contracts, servants and amendments
  share the Transparencia pipeline.
- **61 source IDs were added**, bringing the complete registry to **169 entries**.
  New entries remain `not_implemented` / `not_loaded`. Of these, 60 join the
  public universe. SISBAJUD is retained only as a restricted reference, with
  `public_access_mode=restricted` and `in_universe_v1=false`.
- Sources from the same agency with different datasets retain separate IDs.
  For example, BCB time series are separate from the existing penalties pipeline,
  and DATASUS hospital/mortality data are separate from the CNES pipeline.
- `stj_dados_abertos` and `tesouro_emendas` now reflect the implementations
  already present in the public runner: **47 implemented pipelines**, with these
  two marked `not_loaded`. Their file input contracts are documented below.
- Existing load states were preserved. The PNCP URL was aligned with the API
  endpoint already used by `etl/scripts/download_pncp.py`. Other existing canonical
  URLs were retained: a broader landing page, Swagger page or API documentation
  URL does not replace a pipeline's download endpoint automatically. The
  `catalog_reference` and `catalog_revision` CSV columns point to the exact
  upstream documentation.

The snapshot includes a `registry_source_id` for each page. Its `metadata` fields
are upstream claims, not independently verified endpoint contracts. `review_notes`
flag known scope mismatches: the SIAFI and Tesouro references point to SADIPem;
the state gazette reference points to Querido Diario and does not establish state
coverage. Review these references before implementing a downloader.

### URL health

The upstream snapshot was checked on **2026-10-26 at 22:33 UTC** (19:33 in
America/Sao_Paulo): **62 unique URLs**, of which 46 were reported online, 11
offline, and 5 FTP. These are URL counts, not pipeline or source counts.

Brazil Visible's checker marks HTTP 401/403 responses and network failures as
offline, and does not probe FTP. An online portal does not establish that a
dataset is fresh, an API credential works, or a pipeline can ingest the response.
These observations are kept under `reported_health` in the snapshot and do not
overwrite registry load or data-quality states.

## Working with the data

The repository includes only a [synthetic demo graph](../data/demo/README.md).
See [Reproducibility](reproducibility.md) for local demo and BYO-data workflows.

The two reconciled pipelines expect these files:

| Pipeline | Required input | Format |
|---|---|---|
| `stj_dados_abertos` | `data/stj_dados_abertos/decisoes.csv` | UTF-8 CSV with headers, comma-separated |
| `tesouro_emendas` | `data/tesouro_emendas/emendas_tesouro.csv` | Latin-1 CSV with headers, semicolon-separated |

Schema and authentication details for the external catalog are in the snapshot.
They must be reconciled with each pipeline's own input contract before use.

## Catalog maintenance

After editing the registry, regenerate and validate its derived documentation:

```bash
python3 scripts/generate_data_sources_summary.py
python3 scripts/generate_pipeline_status.py
python3 scripts/generate_data_sources_summary.py --check
python3 scripts/check_public_claims.py --repo-root .
python3 scripts/check_pipeline_contracts.py
python3 scripts/check_pipeline_inputs.py
```

When refreshing the external snapshot, pin a Git revision, retain each page's
source ID mapping, and review dataset scope before merging identities. Preserve
implementation and load states unless there is evidence from the local code or
an ingestion run. Record HTTP observations separately from ingestion state.

Brazil Visible metadata is credited to **Brazil Visible Contributors (2026)**
under the [MIT license](catalogs/brazil_visible_LICENSE.txt). The snapshot records
immutable documentation URLs and the upstream revision for attribution.
