# CLAUDE.md

This file provides guidance to AI assistants (Claude, GitHub Copilot, etc.) when working with this repository.

## Auto-Generated Files — Do Not Edit Manually

The following files are **auto-generated** by the fixture generator (`scripts/run_fixture_generator.sh`) and must **never be edited manually**:

- `src/fixture_data/fixtures/**/*.json` — API response snapshots
- `src/fixture_data/fixture_type_mappings.py` — type mapping file

To modify fixture content, update the generation logic instead:

- **To stabilize a fluctuating field**: add a rule to `src/fixture_generator/field_stabilizer.py`
- **To change what is collected**: modify `src/fixture_generator/api_fixture_collector.py` or related files

After any change, regenerate and verify by running:

```bash
scripts/run_fixture_generator.sh
```

## Workflow

1. Identify the cause of fixture churn (e.g. a dynamic API field)
2. Add a stabilization rule in `field_stabilizer.py`
3. Re-run the fixture generator
4. Verify no unexpected diff remains
5. Copy fixtures to the server repo and run tests
