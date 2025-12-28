"""Field stabilization for fixture generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseModel, JsonValue

    from src.fixture_generator.fixture_types import FixtureAPIResult, JsonDict

# Stabilization constants
DUMMY_COUNT = 1
DOMAND_BID_COOKIE_NAME = "domand_bid"


@dataclass(frozen=True)
class StabilizationInfo:
    """Information about how to stabilize a field."""

    pattern: str
    # JsonValue allows None/dict/list/etc. which is useful for stabilizing nested structures.
    replacement_value: JsonValue
    is_partial_match: bool = False

    def matches(self, field_name: str, path: str) -> bool:
        """Check if this stabilization info matches a field.

        The stabilizer traverses nested JSON structures, so rules can match either:
        - a single field name (e.g. "serverTime")
        - a dotted path (e.g. "watch_data.waku.information")

        For path-based matching, we compare against the full dotted path.
        For field-name matching, we compare against the current field name.
        """
        target = path if "." in self.pattern else field_name
        if self.is_partial_match:
            return self.pattern.lower() in target.lower()
        return self.pattern == target


# Centralized field stabilization rules
STABILIZATION_RULES: list[StabilizationInfo] = [
    # Exact matches
    StabilizationInfo("searchId", "dummy-search-id-for-testing"),
    StabilizationInfo("lastViewedAt", "2025-01-01T00:00:00+09:00"),
    StabilizationInfo("serverTime", "2025-01-01T00:00:00+09:00"),
    StabilizationInfo("registeredAt", "2025-01-01T00:00:00+09:00"),
    StabilizationInfo("nicosid", "dummy_nicosid_for_testing"),
    StabilizationInfo("watchTrackId", "dummy_track_id_for_testing"),
    StabilizationInfo("isPeakTime", False),
    StabilizationInfo("isNicodicArticleExists", False),
    StabilizationInfo(
        "thumbnailUrl", "https://resource.video.nimg.jp/web/img/series/no_thumbnail.png"
    ),
    StabilizationInfo("playbackPosition", 0.0),
    StabilizationInfo("hls_url", "https://dummy.hls.url/for/testing"),
    StabilizationInfo(DOMAND_BID_COOKIE_NAME, "dummy_domand_bid_for_testing"),
    StabilizationInfo("hls_playlist_text", "dummy_hls_playlist_text_for_testing"),
    StabilizationInfo("threadKey", "dummy.jwt.token.for.testing"),
    StabilizationInfo("accessRightKey", "dummy.jwt.token.for.testing"),
    StabilizationInfo("editKey", "dummy.jwt.token.for.testing"),
    StabilizationInfo("views", DUMMY_COUNT),
    # Path / partial-path matches
    # Niconico frequently changes promotional banner info under waku.information.
    # This field is not relevant for provider logic and causes noisy fixture churn.
    StabilizationInfo("waku.information", None, is_partial_match=True),
    # Partial matches
    StabilizationInfo(
        "description", "This is a dummy description for testing purposes.", is_partial_match=True
    ),
]


class FieldStabilizer:
    """Handles stabilization of dynamic fields in fixtures."""

    def __init__(self) -> None:
        """Initialize with stabilization rules."""
        self.rules = STABILIZATION_RULES

    def stabilize[T: BaseModel](self, data: FixtureAPIResult[T]) -> FixtureAPIResult[T]:
        """Stabilize dynamic fields in API responses for consistent fixture generation.

        This function replaces all count-related numeric values with DUMMY_COUNT
        to ensure fixtures are stable across different API response states.
        """
        if isinstance(data, list):
            return [self._stabilize_model(item) for item in data]
        return self._stabilize_model(data)

    def _stabilize_model[T: BaseModel](self, data: T) -> T:
        """Stabilize count values in a single Pydantic model."""
        data_dict = data.model_dump(by_alias=True)
        stabilized_dict = self._stabilize_value(
            key="",
            value=data_dict,
            is_in_count_context=False,
            path="",
        )
        return data.__class__.model_validate(stabilized_dict)

    def _stabilize_value(
        self,
        key: str,
        value: JsonValue,
        is_in_count_context: bool,
        path: str,
    ) -> JsonValue:
        """Stabilize a single value recursively.

        Args:
            key: The field name/key being processed
            value: The value to stabilize
            is_in_count_context: Whether we're inside a count-related field

        Returns:
            Stabilized value
        """
        # 1. Check explicit rules first
        for rule in self.rules:
            if rule.matches(key, path):
                return rule.replacement_value

        # 2. Handle nested structures
        if isinstance(value, dict):
            return self._stabilize_dict(value, is_in_count_context, parent_path=path)
        if isinstance(value, list):
            return [
                self._stabilize_value(key, item, is_in_count_context, path=path) for item in value
            ]

        # 3. Handle count values
        if is_in_count_context and isinstance(value, (int, float)):
            return DUMMY_COUNT

        return value

    def _stabilize_dict(self, data: JsonDict, parent_is_count: bool, parent_path: str) -> JsonDict:
        """Stabilize all fields in a dictionary.

        Args:
            data: Dictionary to stabilize
            parent_is_count: Whether parent was a count field

        Returns:
            Stabilized dictionary
        """
        return {
            k: self._stabilize_value(
                k,
                v,
                parent_is_count or "count" in k.lower(),
                path=f"{parent_path}.{k}" if parent_path else k,
            )
            for k, v in data.items()
        }
