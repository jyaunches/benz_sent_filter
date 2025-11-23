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
        """XFOR case: Should classify as executive_changes."""
        headline = "X4 Pharmaceuticals' President And CEO Paula Ragan And CFO Adam Mostafa Have Stepped Down..."
        result = detector.detect(headline)

        assert result.catalyst_subtype == "executive_changes"
        assert result.confidence >= 0.6

    def test_classify_executive_change_cfo_appointment(self, detector):
        """SHCO case: CFO appointment should classify as executive_changes."""
        headline = "Soho House & Co Inc. Appoints David Bowie As Chief Financial Officer"
        result = detector.detect(headline)

        assert result.catalyst_subtype == "executive_changes"
        assert result.confidence >= 0.6

    def test_classify_merger_agreement_type(self, detector):
        """WKHS case: Should classify as m&a."""
        headline = "Workhorse Group And ATW Partners Announce Merger Agreement"
        result = detector.detect(headline)

        assert result.catalyst_subtype == "m&a"
        assert result.confidence >= 0.6

    def test_classify_product_launch_type(self, detector):
        """SMX case: Should classify as product_launch."""
        headline = "SMX (SECURITY MATTERS) PLC Partners with UN to Launch Global Product Authentication Platform"
        result = detector.detect(headline)

        assert result.catalyst_subtype == "product_launch"
        assert result.confidence >= 0.6

    def test_classify_strategic_partnership_type(self, detector):
        """IMG case: Should classify as partnership."""
        headline = "Imgn Media Signs Mou With Adl Intelligent Labs For Gene-Editing Product Development"
        result = detector.detect(headline)

        assert result.catalyst_subtype == "partnership"
        assert result.confidence >= 0.6

    def test_classify_rebranding_type(self, detector):
        """NEHC case: Should classify as corporate_restructuring."""
        headline = "NorthEast Healthcare Announces Name Change to Alliance HealthCare Services"
        result = detector.detect(headline)

        assert result.catalyst_subtype == "corporate_restructuring"
        assert result.confidence >= 0.6

    def test_classify_clinical_trial_results_type(self, detector):
        """PSTV case: Should classify as clinical_trial."""
        headline = "Positron Announces Positive Phase 1 Clinical Trial Results"
        result = detector.detect(headline)

        assert result.catalyst_subtype == "clinical_trial"
        assert result.confidence >= 0.6


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handle_none_input(self, detector):
        """None input should return negative result."""
        result = detector.detect(None)

        assert result.has_strategic_catalyst is False
        assert result.catalyst_subtype is None
        assert result.confidence == 0.0
        assert result.headline == ""

    def test_handle_empty_string(self, detector):
        """Empty string should return negative result."""
        result = detector.detect("")

        assert result.has_strategic_catalyst is False
        assert result.catalyst_subtype is None
        assert result.confidence == 0.0

    def test_ambiguous_headline_returns_mixed(self, detector):
        """Ambiguous headlines should return 'mixed' if all type scores low."""
        headline = "Company announces major strategic initiative"
        result = detector.detect(headline)

        # This headline might be detected as catalyst but type should be mixed
        # if MNLI can't confidently classify the type
        if result.has_strategic_catalyst:
            # Allow either "mixed" or a valid type with lower confidence
            assert result.catalyst_subtype is not None

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
                "executive_changes",
            ),
            (
                "Soho House & Co Inc. Appoints David Bowie As Chief Financial Officer",
                "executive_changes",
            ),
            ("Opendoor CEO Eric Wu Steps Down", "executive_changes"),
            (
                "Option Care Health Appoints John Rademacher as CFO",
                "executive_changes",
            ),
            (
                "Workhorse Group And ATW Partners Announce Merger Agreement",
                "m&a",
            ),
            (
                "NorthEast Healthcare Announces Name Change to Alliance HealthCare Services",
                "corporate_restructuring",
            ),
            (
                "SMX (SECURITY MATTERS) PLC Partners with UN to Launch Global Product Authentication Platform",
                "product_launch",  # Primary action is "Launch" product - both product_launch and partnership are semantically valid
            ),
            (
                "Citius Pharmaceuticals Launches AI Platform for Drug Development",
                "product_launch",
            ),
            (
                "Imgn Media Signs Mou With Adl Intelligent Labs For Gene-Editing Product Development",
                "partnership",
            ),
            (
                "Workday Partners with IBM on Enterprise AI Solutions",
                "partnership",
            ),
            (
                "Positron Announces Positive Phase 1 Clinical Trial Results",
                "clinical_trial",
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
            result.catalyst_subtype == expected_type
        ), f"Expected {expected_type}, got {result.catalyst_subtype} for: {headline}"
        assert result.confidence >= 0.6, f"Low confidence for: {headline}"


class TestBugFixes:
    """Test fixes for bug benz_sent_filter-edb5: Strategic catalyst classification accuracy issues."""

    def test_quantitative_catalysts_not_detected_as_strategic(self, detector):
        """Issue #1: Quantitative catalysts should NOT be detected as strategic catalysts.

        WOW $1.5B acquisition and WDAY earnings contain dollar amounts and financial
        keywords indicating quantitative catalysts, not strategic transformational events.
        """
        # WOW case: Dollar amount indicates quantitative catalyst (acquisition value)
        wow_headline = "WOW Unlimited Media Acquires Animation Studio for $1.5B"
        wow_result = detector.detect(wow_headline)

        assert wow_result.has_strategic_catalyst is False, (
            f"WOW quantitative catalyst misclassified as strategic: {wow_result.catalyst_subtype}"
        )

        # WDAY case: "earnings" keyword + financial results indicate quantitative catalyst
        wday_headline = "Workday Reports Q4 Earnings Beat with Revenue Growth"
        wday_result = detector.detect(wday_headline)

        assert wday_result.has_strategic_catalyst is False, (
            f"WDAY quantitative catalyst misclassified as strategic: {wday_result.catalyst_subtype}"
        )

    def test_no_mixed_subtype_returned(self, detector):
        """Issue #2: Detector should never return 'mixed' as catalyst_subtype.

        OPEN CEO transition is a clear executive_changes catalyst. The detector
        should return a specific subtype or None, never 'mixed'.
        """
        # OPEN case: Clear CEO departure should classify as executive_changes
        open_headline = "Opendoor CEO Eric Wu Steps Down"
        open_result = detector.detect(open_headline)

        # Should be detected as strategic catalyst
        assert open_result.has_strategic_catalyst is True, (
            "OPEN CEO transition should be detected as strategic catalyst"
        )

        # Should classify as executive_changes, not "mixed"
        assert open_result.catalyst_subtype == "executive_changes", (
            f"Expected 'executive_changes', got '{open_result.catalyst_subtype}'"
        )

        # Subtype should never be "mixed" for any detected catalyst
        assert open_result.catalyst_subtype != "mixed", (
            "'mixed' is not a valid catalyst_subtype value"
        )

    def test_product_launch_detection_sensitivity(self, detector):
        """Issue #3: Product launches should be detected (false negative fix).

        CTXR AI platform launch and MURA product announcement are clear strategic
        catalysts but were not detected. Improve detection sensitivity.
        """
        # CTXR case: AI platform launch should be detected
        ctxr_headline = "Citius Pharmaceuticals Launches AI Platform for Drug Development"
        ctxr_result = detector.detect(ctxr_headline)

        assert ctxr_result.has_strategic_catalyst is True, (
            "CTXR product launch not detected as strategic catalyst"
        )
        assert ctxr_result.catalyst_subtype == "product_launch", (
            f"CTXR expected 'product_launch', got '{ctxr_result.catalyst_subtype}'"
        )

        # MURA case: Product announcement should be detected
        # Note: Medical/biotech product announcements are ambiguous - could be product_launch
        # or clinical_trial depending on context. Both are acceptable for this edge case.
        mura_headline = "Mural Oncology Announces New Cancer Treatment Product"
        mura_result = detector.detect(mura_headline)

        assert mura_result.has_strategic_catalyst is True, (
            "MURA product announcement not detected as strategic catalyst"
        )
        assert mura_result.catalyst_subtype in ["product_launch", "clinical_trial"], (
            f"MURA expected 'product_launch' or 'clinical_trial', got '{mura_result.catalyst_subtype}'"
        )


class TestProductionHeadlines:
    """Test production headlines from benz_sent_filter-20cc evaluation runs.

    These are the actual headlines that failed in production, representing
    real-world messy data with extra context, hype language, and noise.
    """

    def test_production_nehc_corporate_restructuring(self, detector):
        """NEHC: Name and ticker change should be detected as corporate_restructuring.

        Production issue: Was NOT detected (false negative).
        Actual move: +22.7%
        """
        headline = "New Era Helium Changes Name To New Era Energy & Digital; To Trade Under New Ticker 'NUAI'"
        result = detector.detect(headline)

        assert result.has_strategic_catalyst is True, (
            f"NEHC name/ticker change not detected: {headline}"
        )
        assert result.catalyst_subtype == "corporate_restructuring", (
            f"NEHC expected 'corporate_restructuring', got '{result.catalyst_subtype}'"
        )

    def test_production_xfor_triple_executive_changes(self, detector):
        """XFOR: Triple C-suite transition (3 executives!) should be detected.

        Production issue: Was NOT detected (false negative).
        Actual move: +85.9% (HUGE!)
        Note: Multiple C-suite changes in one announcement - very significant catalyst.
        """
        headline = "X4 Pharmaceuticals' President And CEO Paula Ragan And CFO Adam Mostafa Have Stepped Down From Their Respective Roles, X4 Board Of Directors Has Appointed Adam Craig, As Executive Chair, John Volpone As President, And David Kirske As CFO Effectively Immediately"
        result = detector.detect(headline)

        assert result.has_strategic_catalyst is True, (
            f"XFOR triple C-suite change not detected: {headline[:100]}..."
        )
        assert result.catalyst_subtype == "executive_changes", (
            f"XFOR expected 'executive_changes', got '{result.catalyst_subtype}'"
        )

    def test_production_smx_product_launch_with_context(self, detector):
        """SMX: Product launch with UN partnership context should be detected.

        Production issue: Was NOT detected (false negative).
        Actual move: +37.4%
        Note: Has explicit "Launches" keyword with new product/platform.
        """
        headline = "SMX Launches Global Plastics Passport to Track and Monetize All Plastics, Offers Tech Free to Support UN Treaty"
        result = detector.detect(headline)

        assert result.has_strategic_catalyst is True, (
            f"SMX product launch not detected: {headline}"
        )
        assert result.catalyst_subtype == "product_launch", (
            f"SMX expected 'product_launch', got '{result.catalyst_subtype}'"
        )

    def test_production_wow_quantitative_should_be_filtered(self, detector):
        """WOW: Headline with $1.5B deal price should NOT be strategic (quantitative filter).

        Production issue: Was detected as strategic with wrong subtype.
        Expected: Quantitative pre-filter should reject (has dollar amount).
        """
        headline = "WOW! Stock Rockets As DigitalBridge Strikes $1.5 Billion Deal"
        result = detector.detect(headline)

        assert result.has_strategic_catalyst is False, (
            f"WOW with $1.5B should be filtered as quantitative: {headline}"
        )

    def test_production_mura_quantitative_with_per_share_price(self, detector):
        """MURA: Acquisition with per-share price should NOT be strategic.

        Production note: Was correctly NOT detected (quantitative filter working).
        Has explicit per-share price ($2.035-$2.24/share).
        """
        headline = "Mural Oncology To be Acquired By Xoma Royalty Subsidiary, XRA 5, For between $2.035 And $2.24 In Cash Per Share"
        result = detector.detect(headline)

        assert result.has_strategic_catalyst is False, (
            f"MURA with per-share price should be filtered as quantitative: {headline}"
        )
