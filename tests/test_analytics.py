"""Analytics aggregation checks."""
import pytest

from underwritekit.analytics import credit_band, dti_band, run_analytics

REPORT = run_analytics(5000, seed=31)


def test_overall_rate_consistent():
    assert REPORT["applications"] == 5000
    assert REPORT["overall_approval_rate"] == round(REPORT["approved"] / 5000, 4)
    assert 0 < REPORT["overall_approval_rate"] < 1


def test_segments_partition_population():
    for segment in ("occupancy", "units", "credit_band", "dti_band"):
        table = REPORT["approval_by_segment"][segment]
        assert sum(row["applications"] for row in table.values()) == 5000
        assert sum(row["approved"] for row in table.values()) == REPORT["approved"]


def test_reason_codes_are_known():
    known = {"LIM01", "LTV01", "CRD01", "CRD02", "DTI01", "DTI02", "DTI03", "RSV01"}
    assert set(REPORT["reason_code_frequency"]) <= known
    assert REPORT["reason_code_frequency"]


@pytest.mark.parametrize(
    "score,band",
    [(619, "under_620"), (620, "620_659"), (659, "620_659"), (660, "660_719"),
     (719, "660_719"), (720, "720_plus")],
)
def test_credit_bands(score, band):
    assert credit_band(score) == band


@pytest.mark.parametrize(
    "debt,band",
    [(360000, "le_36"), (360001, "36_45"), (450000, "36_45"),
     (450001, "45_50"), (500000, "45_50"), (500001, "over_50")],
)
def test_dti_bands(debt, band):
    assert dti_band(debt, 1000000) == band
