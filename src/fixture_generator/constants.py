"""Common constants for nicovideo fixture generation."""

from __future__ import annotations

import pathlib

# Test fixtures directories
_BASE_DIR = pathlib.Path(__file__).parent.parent
FIXTURE_DATA_DIR = _BASE_DIR / "fixture_data"
GENERATED_FIXTURES_DIR = FIXTURE_DATA_DIR / "fixtures"
GENERATED_FIXTURE_TYPES_PATH = FIXTURE_DATA_DIR / "fixture_type_mappings.py"

# Machine-readable list of fixtures that failed to collect, written relative to the
# working directory so tooling can report failures without parsing the run log
COLLECTION_FAILURE_REPORT_PATH = pathlib.Path("fixture-failures.txt")

# Sample test data IDs
SAMPLE_VIDEO_ID = "sm45285955"
SAMPLE_USER_ID = "68461151"
SAMPLE_MYLIST_ID = "78597499"
SAMPLE_SERIES_ID = "527007"
