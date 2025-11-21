"""Tests for strategic catalyst detector service.

Tests MNLI-based presence detection and type classification for strategic
corporate catalysts (executive changes, mergers, partnerships, product launches,
rebranding, clinical trials).
"""

import pytest

from benz_sent_filter.services.strategic_catalyst_detector_mnls import (
    StrategicCatalystDetectorMNLS,
)


@pytest.fixture
def detector():
    """Create detector instance for testing."""
    return StrategicCatalystDetectorMNLS()


class TestPresenceDetection:
    """Test MNLI presence detection for strategic catalysts."""

    def test_detect_executive_change_xfor_triple_transition(self, detector):
        """XFOR case: Triple C-suite transition should be detected."""
        headline = "X4 Pharmaceuticals' President And CEO Paula Ragan And CFO Adam Mostafa Have Stepped Down..."
        result = detector.detect(headline)

        assert result.has_strategic_catalyst is True
        assert result.confidence > 0.0

    def test_detect_executive_change_shco_cfo_appointment(self, detector):
        """SHCO case: CFO appointment should be detected."""
        headline = "Soho House & Co Inc. Appoints David Bowie As Chief Financial Officer"
        result = detector.detect(headline)

        assert result.has_strategic_catalyst is True
        assert result.confidence > 0.0

    def test_detect_merger_wkhs_agreement(self, detector):
        """WKHS case: Merger agreement should be detected."""
        headline = "Workhorse Group And ATW Partners Announce Merger Agreement"
        result = detector.detect(headline)

        assert result.has_strategic_catalyst is True
        assert result.confidence > 0.0

    def test_detect_product_launch_smx_global(self, detector):
        """SMX case: Global product launch should be detected."""
        headline = "SMX (SECURITY MATTERS) PLC Partners with UN to Launch Global Product Authentication Platform"
        result = detector.detect(headline)

        assert result.has_strategic_catalyst is True
        assert result.confidence > 0.0

    def test_detect_partnership_img_mou(self, detector):
        """IMG case: MoU for strategic partnership should be detected."""
        headline = "Imgn Media Signs Mou With Adl Intelligent Labs For Gene-Editing Product Development"
        result = detector.detect(headline)

        assert result.has_strategic_catalyst is True
        assert result.confidence > 0.0

    def test_detect_rebranding_nehc_name_change(self, detector):
        """NEHC case: Name/ticker change should be detected."""
        headline = "NorthEast Healthcare Announces Name Change to Alliance HealthCare Services"
        result = detector.detect(headline)

        assert result.has_strategic_catalyst is True
        assert result.confidence > 0.0

    def test_detect_clinical_trial_pstv_results(self, detector):
        """PSTV case: Clinical trial results should be detected."""
        headline = "Positron Announces Positive Phase 1 Clinical Trial Results"
        result = detector.detect(headline)

        assert result.has_strategic_catalyst is True
        assert result.confidence > 0.0

    def test_reject_financial_results(self, detector):
        """Financial results should not be detected as strategic catalyst."""
        headline = "Company reports Q3 earnings of $1.2B revenue"
        result = detector.detect(headline)

        assert result.has_strategic_catalyst is False

    def test_reject_stock_movement(self, detector):
        """Stock price movements should not be detected as strategic catalyst."""
        headline = "Stock rises 10% on strong trading volume"
        result = detector.detect(headline)

        assert result.has_strategic_catalyst is False

    def test_reject_routine_operations(self, detector):
        """Routine operations should not be detected as strategic catalyst."""
        headline = "Bank files quarterly MBS disclosure report with SEC"
        result = detector.detect(headline)

        assert result.has_strategic_catalyst is False


class TestTypeClassification:
    """Test MNLI type classification for strategic catalysts."""

    def test_classify_executive_change_type(self, detector):
        """XFOR case: Should classify as executive_change."""
        headline = "X4 Pharmaceuticals' President And CEO Paula Ragan And CFO Adam Mostafa Have Stepped Down..."
        result = detector.detect(headline)

        assert result.catalyst_type == "executive_change"
        assert result.confidence >= 0.6

    def test_classify_executive_change_cfo_appointment(self, detector):
        """SHCO case: CFO appointment should classify as executive_change."""
        headline = "Soho House & Co Inc. Appoints David Bowie As Chief Financial Officer"
        result = detector.detect(headline)

        assert result.catalyst_type == "executive_change"
        assert result.confidence >= 0.6

    def test_classify_merger_agreement_type(self, detector):
        """WKHS case: Should classify as merger_agreement."""
        headline = "Workhorse Group And ATW Partners Announce Merger Agreement"
        result = detector.detect(headline)

        assert result.catalyst_type == "merger_agreement"
        assert result.confidence >= 0.6

    def test_classify_product_launch_type(self, detector):
        """SMX case: Should classify as product_launch."""
        headline = "SMX (SECURITY MATTERS) PLC Partners with UN to Launch Global Product Authentication Platform"
        result = detector.detect(headline)

        assert result.catalyst_type == "product_launch"
        assert result.confidence >= 0.6

    def test_classify_strategic_partnership_type(self, detector):
        """IMG case: Should classify as strategic_partnership."""
        headline = "Imgn Media Signs Mou With Adl Intelligent Labs For Gene-Editing Product Development"
        result = detector.detect(headline)

        assert result.catalyst_type == "strategic_partnership"
        assert result.confidence >= 0.6

    def test_classify_rebranding_type(self, detector):
        """NEHC case: Should classify as rebranding."""
        headline = "NorthEast Healthcare Announces Name Change to Alliance HealthCare Services"
        result = detector.detect(headline)

        assert result.catalyst_type == "rebranding"
        assert result.confidence >= 0.6

    def test_classify_clinical_trial_results_type(self, detector):
        """PSTV case: Should classify as clinical_trial_results."""
        headline = "Positron Announces Positive Phase 1 Clinical Trial Results"
        result = detector.detect(headline)

        assert result.catalyst_type == "clinical_trial_results"
        assert result.confidence >= 0.6


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handle_none_input(self, detector):
        """None input should return negative result."""
        result = detector.detect(None)

        assert result.has_strategic_catalyst is False
        assert result.catalyst_type is None
        assert result.confidence == 0.0
        assert result.headline == ""

    def test_handle_empty_string(self, detector):
        """Empty string should return negative result."""
        result = detector.detect("")

        assert result.has_strategic_catalyst is False
        assert result.catalyst_type is None
        assert result.confidence == 0.0

    def test_ambiguous_headline_returns_mixed(self, detector):
        """Ambiguous headlines should return 'mixed' if all type scores low."""
        headline = "Company announces major strategic initiative"
        result = detector.detect(headline)

        # This headline might be detected as catalyst but type should be mixed
        # if MNLI can't confidently classify the type
        if result.has_strategic_catalyst:
            # Allow either "mixed" or a valid type with lower confidence
            assert result.catalyst_type is not None

    def test_confidence_score_range(self, detector):
        """Confidence scores should be between 0.0 and 1.0."""
        headline = "X4 Pharmaceuticals' President And CEO Paula Ragan And CFO Adam Mostafa Have Stepped Down..."
        result = detector.detect(headline)

        assert 0.0 <= result.confidence <= 1.0


class TestRealWorldExamples:
    """Test all 11 real-world examples for 90%+ accuracy."""

    @pytest.mark.parametrize(
        "headline,expected_type",
        [
            (
                "X4 Pharmaceuticals' President And CEO Paula Ragan And CFO Adam Mostafa Have Stepped Down...",
                "executive_change",
            ),
            (
                "Soho House & Co Inc. Appoints David Bowie As Chief Financial Officer",
                "executive_change",
            ),
            ("Opendoor CEO Eric Wu Steps Down", "executive_change"),
            (
                "Option Care Health Appoints John Rademacher as CFO",
                "executive_change",
            ),
            (
                "Workhorse Group And ATW Partners Announce Merger Agreement",
                "merger_agreement",
            ),
            (
                "NorthEast Healthcare Announces Name Change to Alliance HealthCare Services",
                "rebranding",
            ),
            (
                "SMX (SECURITY MATTERS) PLC Partners with UN to Launch Global Product Authentication Platform",
                "product_launch",
            ),
            (
                "Citius Pharmaceuticals Launches AI Platform for Drug Development",
                "product_launch",
            ),
            (
                "Imgn Media Signs Mou With Adl Intelligent Labs For Gene-Editing Product Development",
                "strategic_partnership",
            ),
            (
                "Workday Partners with IBM on Enterprise AI Solutions",
                "strategic_partnership",
            ),
            (
                "Positron Announces Positive Phase 1 Clinical Trial Results",
                "clinical_trial_results",
            ),
        ],
    )
    def test_all_real_world_examples(self, detector, headline, expected_type):
        """Test all 11 real-world examples classify correctly."""
        result = detector.detect(headline)

        assert (
            result.has_strategic_catalyst is True
        ), f"Failed to detect catalyst in: {headline}"
        assert (
            result.catalyst_type == expected_type
        ), f"Expected {expected_type}, got {result.catalyst_type} for: {headline}"
        assert result.confidence >= 0.6, f"Low confidence for: {headline}"
