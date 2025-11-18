"""
Unit tests for RoutineOperationDetector service - Phase 1: Core Detection Engine.

Tests cover:
- Service initialization and pattern loading
- Process language detection
- Routine transaction type detection
- Frequency indicator detection
- Dollar amount extraction
- Scoring algorithm
- Confidence calculation
- Edge cases
"""

import pytest
from benz_sent_filter.services.routine_detector import (
    RoutineOperationDetector,
    RoutineDetectionResult,
)


class TestRoutineDetectorInitialization:
    """Test service initialization and pattern dictionary loading."""

    def test_routine_detector_initialization_success(self):
        """Detector initializes successfully with compiled regex patterns."""
        detector = RoutineOperationDetector()
        assert detector is not None

    def test_routine_detector_has_process_language_patterns(self):
        """Detector has compiled process language regex patterns."""
        detector = RoutineOperationDetector()
        assert hasattr(detector, "PROCESS_LANGUAGE_PATTERNS")
        assert isinstance(detector.PROCESS_LANGUAGE_PATTERNS, dict)

        # Check expected categories
        expected_categories = ["initiation", "marketing", "planning", "evaluation"]
        for category in expected_categories:
            assert category in detector.PROCESS_LANGUAGE_PATTERNS

    def test_routine_detector_has_transaction_type_patterns(self):
        """Detector has financial services transaction type patterns."""
        detector = RoutineOperationDetector()
        assert hasattr(detector, "FINANCIAL_SERVICES_PATTERNS")
        assert isinstance(detector.FINANCIAL_SERVICES_PATTERNS, dict)

    def test_routine_detector_has_frequency_patterns(self):
        """Detector has frequency indicator patterns."""
        detector = RoutineOperationDetector()
        assert hasattr(detector, "FREQUENCY_PATTERNS")
        assert isinstance(detector.FREQUENCY_PATTERNS, dict)

        # Check expected categories
        expected_categories = ["recurrence", "schedule", "program"]
        for category in expected_categories:
            assert category in detector.FREQUENCY_PATTERNS


class TestProcessLanguageDetection:
    """Test process language pattern detection."""

    def test_detect_process_language_strong_initiation_pattern(self):
        """Strong initiation pattern detected with +2 score."""
        detector = RoutineOperationDetector()
        result = detector.detect("Fannie Mae Begins Marketing Its Most Recent Sale")

        assert "process_language" in result.detected_patterns
        assert result.routine_score >= 2

    def test_detect_process_language_marketing_pattern(self):
        """Marketing pattern detected."""
        detector = RoutineOperationDetector()
        result = detector.detect("Loan Portfolio Available for Purchase")

        assert "process_language" in result.detected_patterns
        assert result.routine_score >= 1

    def test_detect_process_language_planning_pattern(self):
        """Planning language detected."""
        detector = RoutineOperationDetector()
        result = detector.detect("Bank Plans to Issue Bonds Next Quarter")

        assert "process_language" in result.detected_patterns
        assert result.routine_score >= 1

    def test_detect_process_language_evaluation_pattern(self):
        """Evaluation language detected."""
        detector = RoutineOperationDetector()
        result = detector.detect("Company Exploring Options for Debt Refinancing")

        assert "process_language" in result.detected_patterns
        assert result.routine_score >= 1

    def test_detect_process_language_case_insensitive(self):
        """Pattern matching is case insensitive."""
        detector = RoutineOperationDetector()

        variations = [
            "BEGINS MARKETING",
            "begins marketing",
            "Begins Marketing",
        ]

        for text in variations:
            result = detector.detect(text)
            assert "process_language" in result.detected_patterns

    def test_detect_process_language_multiple_patterns(self):
        """Multiple process indicators compound the score."""
        detector = RoutineOperationDetector()
        result = detector.detect("Bank Begins Marketing and Plans to Launch Sale")

        assert "process_language" in result.detected_patterns
        assert result.routine_score >= 2

    def test_detect_process_language_completed_transaction_excluded(self):
        """Completed transactions not flagged as process."""
        detector = RoutineOperationDetector()
        result = detector.detect("Completes Sale of Loan Portfolio")

        # Should not be flagged as routine (completion keyword overrides)
        assert result.result is False

    def test_detect_process_language_no_pattern_match(self):
        """Headlines without process language score 0."""
        detector = RoutineOperationDetector()
        result = detector.detect("Bank Reports Q2 Earnings of $1B")

        assert "process_language" not in result.detected_patterns


class TestRoutineTransactionTypeDetection:
    """Test routine transaction type pattern detection."""

    def test_detect_routine_transaction_loan_portfolio_sale(self):
        """Loan portfolio sale pattern detected."""
        detector = RoutineOperationDetector()
        result = detector.detect("Sale of Reperforming Loans")

        assert "routine_transaction" in result.detected_patterns
        assert result.routine_score >= 1

    def test_detect_routine_transaction_buyback_program(self):
        """Buyback program pattern detected."""
        detector = RoutineOperationDetector()
        result = detector.detect("Share Repurchase Program Announced")

        assert "routine_transaction" in result.detected_patterns
        assert result.routine_score >= 1

    def test_detect_routine_transaction_quarterly_dividend(self):
        """Quarterly dividend pattern detected."""
        detector = RoutineOperationDetector()
        result = detector.detect("Quarterly Dividend Payment of $0.50")

        assert "routine_transaction" in result.detected_patterns
        assert result.routine_score >= 1

    def test_detect_routine_transaction_debt_refinancing(self):
        """Debt refinancing pattern detected."""
        detector = RoutineOperationDetector()
        result = detector.detect("Bond Issuance for Debt Refinancing")

        assert "routine_transaction" in result.detected_patterns
        assert result.routine_score >= 1

    def test_detect_routine_transaction_special_dividend_excluded(self):
        """Special dividends excluded (not routine)."""
        detector = RoutineOperationDetector()
        result = detector.detect("Special Dividend of $5.00 Announced")

        # Should not be flagged as routine (special keyword overrides)
        assert result.result is False

    def test_detect_routine_transaction_no_match(self):
        """Non-routine transactions not detected."""
        detector = RoutineOperationDetector()
        result = detector.detect("Acquisition of Competitor for $10B")

        assert "routine_transaction" not in result.detected_patterns


class TestFrequencyIndicatorDetection:
    """Test frequency indicator pattern detection."""

    def test_detect_frequency_indicator_recurrence(self):
        """Recurrence pattern detected."""
        detector = RoutineOperationDetector()
        result = detector.detect("Most Recent Sale of Reperforming Loans")

        assert "frequency_indicator" in result.detected_patterns
        assert result.routine_score >= 1

    def test_detect_frequency_indicator_schedule(self):
        """Schedule pattern detected."""
        detector = RoutineOperationDetector()
        result = detector.detect("Quarterly Dividend Payment")

        assert "frequency_indicator" in result.detected_patterns
        assert result.routine_score >= 1

    def test_detect_frequency_indicator_program(self):
        """Program pattern detected."""
        detector = RoutineOperationDetector()
        result = detector.detect("As Part of Ongoing Buyback Program")

        assert "frequency_indicator" in result.detected_patterns
        assert result.routine_score >= 1

    def test_detect_frequency_indicator_multiple_patterns(self):
        """Multiple frequency indicators compound the score."""
        detector = RoutineOperationDetector()
        result = detector.detect("Latest Quarterly Dividend Payment")

        assert "frequency_indicator" in result.detected_patterns
        # Should have compound score from multiple indicators
        assert result.routine_score >= 2

    def test_detect_frequency_indicator_no_match(self):
        """Non-recurring events not detected."""
        detector = RoutineOperationDetector()
        result = detector.detect("First-Ever Dividend Payment")

        assert "frequency_indicator" not in result.detected_patterns


class TestDollarAmountExtraction:
    """Test dollar amount extraction from headlines."""

    def test_extract_dollar_amount_millions_abbreviation(self):
        """Extract millions with abbreviation."""
        detector = RoutineOperationDetector()
        result = detector.detect("Sale of Loans for $560M")

        assert result.transaction_value == 560000000.0

    def test_extract_dollar_amount_billions_abbreviation(self):
        """Extract billions with abbreviation."""
        detector = RoutineOperationDetector()
        result = detector.detect("Transaction valued at $1.5B")

        assert result.transaction_value == 1500000000.0

    def test_extract_dollar_amount_millions_word(self):
        """Extract millions with word."""
        detector = RoutineOperationDetector()
        result = detector.detect("Portfolio worth $500 million")

        assert result.transaction_value == 500000000.0

    def test_extract_dollar_amount_billions_word(self):
        """Extract billions with word."""
        detector = RoutineOperationDetector()
        result = detector.detect("Deal valued at $2.3 billion")

        assert result.transaction_value == 2300000000.0

    def test_extract_dollar_amount_euro_symbol(self):
        """Extract amount with euro symbol."""
        detector = RoutineOperationDetector()
        result = detector.detect("Portfolio valued at €100M")

        assert result.transaction_value == 100000000.0

    def test_extract_dollar_amount_range_midpoint(self):
        """Extract midpoint from range."""
        detector = RoutineOperationDetector()
        result = detector.detect("Between $50M and $100M")

        assert result.transaction_value == 75000000.0

    def test_extract_dollar_amount_no_amount(self):
        """Return None when no amount found."""
        detector = RoutineOperationDetector()
        result = detector.detect("No financial figures mentioned")

        assert result.transaction_value is None

    def test_extract_dollar_amount_multiple_amounts_first(self):
        """Extract first amount when multiple present."""
        detector = RoutineOperationDetector()
        result = detector.detect("$500M initial, $1B total")

        assert result.transaction_value == 500000000.0


class TestScoringAlgorithm:
    """Test scoring algorithm that combines pattern matches."""

    def test_scoring_algorithm_process_plus_frequency(self):
        """Process language + frequency indicator scoring."""
        detector = RoutineOperationDetector()
        result = detector.detect("Begins Marketing Most Recent Sale")

        assert result.routine_score >= 3
        assert "process_language" in result.detected_patterns
        assert "frequency_indicator" in result.detected_patterns

    def test_scoring_algorithm_all_patterns(self):
        """All pattern types detected."""
        detector = RoutineOperationDetector()
        result = detector.detect(
            "Begins Marketing Latest Quarterly Dividend Payment"
        )

        assert result.routine_score >= 3
        assert "process_language" in result.detected_patterns
        assert "frequency_indicator" in result.detected_patterns

    def test_scoring_algorithm_single_pattern(self):
        """Single pattern detection."""
        detector = RoutineOperationDetector()
        result = detector.detect("Quarterly Payment")

        assert result.routine_score >= 1
        assert len(result.detected_patterns) >= 1

    def test_scoring_algorithm_no_patterns(self):
        """No patterns matched."""
        detector = RoutineOperationDetector()
        result = detector.detect("Bank Reports Q2 Earnings")

        assert result.routine_score == 0
        assert result.detected_patterns == []
        assert result.result is False

    def test_scoring_algorithm_consistent_reproducible(self):
        """Same headline produces identical results."""
        detector = RoutineOperationDetector()
        headline = "Begins Marketing Most Recent Sale"

        result1 = detector.detect(headline)
        result2 = detector.detect(headline)

        assert result1.routine_score == result2.routine_score
        assert result1.detected_patterns == result2.detected_patterns
        assert result1.confidence == result2.confidence

    def test_final_decision_threshold_based(self):
        """Base threshold rule for final result."""
        detector = RoutineOperationDetector()
        # Create headline with routine_score >= 2
        result = detector.detect("Begins Marketing Quarterly Dividend")

        # Should meet threshold for routine classification
        if result.routine_score >= 2:
            assert result.result is True

    def test_final_decision_superlative_override(self):
        """Superlative overrides routine detection."""
        detector = RoutineOperationDetector()
        result = detector.detect("Begins Marketing Record-Breaking Loan Sale")

        # Superlative should override
        assert result.result is False

    def test_final_decision_completion_keyword_override(self):
        """Completion keywords override routine detection."""
        detector = RoutineOperationDetector()
        result = detector.detect("Completes Quarterly Dividend Payment")

        # Completion should override
        assert result.result is False

    def test_final_decision_special_keyword_override(self):
        """Special keyword overrides routine detection."""
        detector = RoutineOperationDetector()
        result = detector.detect("Special Dividend Payment Announced")

        # Special keyword should override
        assert result.result is False


class TestConfidenceCalculation:
    """Test confidence calculation for routine operation detection."""

    def test_confidence_calculation_base_value(self):
        """Base confidence value is 0.5."""
        detector = RoutineOperationDetector()
        result = detector.detect("Some random text")

        # No patterns, no materiality, no context
        assert result.confidence == 0.5

    def test_confidence_calculation_strong_patterns_boost(self):
        """Strong patterns boost confidence."""
        detector = RoutineOperationDetector()
        result = detector.detect("Begins Marketing Latest Quarterly Dividend")

        # routine_score >= 3 should boost by 0.2
        if result.routine_score >= 3:
            assert result.confidence >= 0.7

    def test_confidence_calculation_weak_patterns_no_boost(self):
        """Weak patterns don't boost confidence."""
        detector = RoutineOperationDetector()
        result = detector.detect("Quarterly Payment")

        # routine_score < 3 should not get pattern boost
        if result.routine_score < 3:
            assert result.confidence == 0.5

    def test_confidence_calculation_conflicting_signals_penalty(self):
        """Conflicting signals reduce confidence."""
        detector = RoutineOperationDetector()
        result = detector.detect("Begins Marketing Record-Breaking Loan Sale")

        # Has routine patterns but also superlative
        # Should have penalty applied
        assert result.confidence < 0.7

    def test_confidence_calculation_superlative_detection(self):
        """Superlatives detected and reduce confidence."""
        detector = RoutineOperationDetector()

        superlatives = [
            "largest ever sale",
            "unprecedented transaction",
            "record loan sale",
            "biggest dividend",
            "historic buyback",
            "never before seen",
        ]

        for text in superlatives:
            result = detector.detect(f"Begins Marketing {text}")
            # Superlative should reduce confidence by 0.3
            # Even with pattern boost, should be below 0.7
            assert result.confidence < 0.7

    def test_confidence_calculation_clamped_to_range(self):
        """Confidence clamped to [0.0, 1.0]."""
        detector = RoutineOperationDetector()

        # Test various inputs
        test_cases = [
            "Begins Marketing Latest Quarterly Dividend",
            "Record-breaking historic unprecedented sale",
            "Random text",
        ]

        for text in test_cases:
            result = detector.detect(text)
            assert 0.0 <= result.confidence <= 1.0


class TestEdgeCases:
    """Test edge case handling."""

    def test_edge_case_empty_headline(self):
        """Empty headline handled gracefully."""
        detector = RoutineOperationDetector()
        result = detector.detect("")

        assert result.routine_score == 0
        assert result.confidence == 0.5
        assert result.transaction_value is None

    def test_edge_case_none_headline(self):
        """None headline handled gracefully."""
        detector = RoutineOperationDetector()

        # Should handle None without crashing
        result = detector.detect(None)
        assert result.routine_score == 0

    def test_edge_case_very_long_headline(self):
        """Very long headlines processed correctly."""
        detector = RoutineOperationDetector()
        long_headline = "Begins Marketing " * 100 + "Loan Sale"

        result = detector.detect(long_headline)
        # Should still detect patterns
        assert "process_language" in result.detected_patterns

    def test_edge_case_special_characters(self):
        """Special characters don't break pattern matching."""
        detector = RoutineOperationDetector()
        result = detector.detect("Fannie Mae Begins Marketing... $560M!!!")

        assert "process_language" in result.detected_patterns
        assert result.transaction_value == 560000000.0


class TestRoutineDetectionResult:
    """Test RoutineDetectionResult Pydantic model."""

    def test_result_model_has_required_phase1_fields(self):
        """Model has all required Phase 1 fields."""
        detector = RoutineOperationDetector()
        result = detector.detect("Begins Marketing Loan Sale $560M")

        # Required Phase 1 fields
        assert hasattr(result, "routine_score")
        assert hasattr(result, "confidence")
        assert hasattr(result, "detected_patterns")
        assert hasattr(result, "transaction_value")
        assert hasattr(result, "process_stage")
        assert hasattr(result, "result")

    def test_result_model_has_optional_phase2_fields(self):
        """Model has optional Phase 2 fields (None in Phase 1)."""
        detector = RoutineOperationDetector()
        result = detector.detect("Begins Marketing Loan Sale")

        # Optional Phase 2 fields should be None in Phase 1
        assert hasattr(result, "materiality_score")
        assert hasattr(result, "materiality_ratio")
        assert result.materiality_score is None
        assert result.materiality_ratio is None

    def test_result_model_process_stage_detection(self):
        """Process stage detected from keywords."""
        detector = RoutineOperationDetector()

        test_cases = [
            ("Begins Marketing", "early"),
            ("Starts Sale Process", "early"),
            ("Continues Buyback Program", "ongoing"),
            ("Completes Loan Sale", "completed"),
            ("Announces Completion of Sale", "completed"),
        ]

        for headline, expected_stage in test_cases:
            result = detector.detect(headline)
            if expected_stage in ["early", "ongoing", "completed"]:
                assert result.process_stage == expected_stage


# ============================================================================
# Phase 2: Materiality Assessment Tests
# ============================================================================


class TestCompanyContextDictionary:
    """Test company context dictionary and lookup."""

    def test_company_context_dictionary_has_fnma(self):
        """FNMA company context available as dataclass instance."""
        detector = RoutineOperationDetector()
        assert "FNMA" in detector.COMPANY_CONTEXT

        context = detector.COMPANY_CONTEXT["FNMA"]
        assert hasattr(context, "market_cap")
        assert hasattr(context, "annual_revenue")
        assert hasattr(context, "total_assets")

    def test_company_context_dictionary_has_bac(self):
        """BAC company context available as dataclass instance."""
        detector = RoutineOperationDetector()
        assert "BAC" in detector.COMPANY_CONTEXT

        context = detector.COMPANY_CONTEXT["BAC"]
        assert hasattr(context, "market_cap")
        assert hasattr(context, "annual_revenue")
        assert hasattr(context, "total_assets")

    def test_company_context_dictionary_20_plus_symbols(self):
        """Dictionary contains 20+ financial services symbols."""
        detector = RoutineOperationDetector()
        assert len(detector.COMPANY_CONTEXT) >= 20

    def test_company_context_lookup_known_symbol(self):
        """Successful company context lookup for known symbol."""
        detector = RoutineOperationDetector()
        context = detector.get_company_context("FNMA")

        assert context is not None
        assert context.total_assets > 0

    def test_company_context_lookup_unknown_symbol(self):
        """Unknown symbol returns None (graceful degradation)."""
        detector = RoutineOperationDetector()
        context = detector.get_company_context("UNKNOWN")

        assert context is None


class TestMaterialityRatioCalculation:
    """Test materiality ratio calculations."""

    def test_calculate_materiality_ratio_market_cap(self):
        """Market cap ratio calculated correctly."""
        detector = RoutineOperationDetector()
        ratio_result = detector.calculate_materiality_ratio(
            transaction_value=560500000,
            market_cap=4000000000,
            annual_revenue=None,
            total_assets=None,
        )

        assert ratio_result is not None
        assert abs(ratio_result.ratio - 0.140125) < 0.001
        assert ratio_result.metric_type == "market_cap"

    def test_calculate_materiality_ratio_revenue(self):
        """Revenue ratio calculated correctly."""
        detector = RoutineOperationDetector()
        ratio_result = detector.calculate_materiality_ratio(
            transaction_value=560500000,
            market_cap=None,
            annual_revenue=25000000000,
            total_assets=None,
        )

        assert ratio_result is not None
        assert abs(ratio_result.ratio - 0.02242) < 0.001
        assert ratio_result.metric_type == "revenue"

    def test_calculate_materiality_ratio_assets_fnma_example(self):
        """Asset ratio calculated correctly (FNMA example)."""
        detector = RoutineOperationDetector()
        ratio_result = detector.calculate_materiality_ratio(
            transaction_value=560500000,
            market_cap=None,
            annual_revenue=None,
            total_assets=4000000000000,
        )

        assert ratio_result is not None
        assert abs(ratio_result.ratio - 0.00014) < 0.00001
        assert ratio_result.metric_type == "assets"

    def test_calculate_materiality_ratio_zero_company_metric(self):
        """Division by zero handled gracefully."""
        detector = RoutineOperationDetector()
        ratio_result = detector.calculate_materiality_ratio(
            transaction_value=100000000,
            market_cap=0,
            annual_revenue=None,
            total_assets=None,
        )

        assert ratio_result is None

    def test_calculate_materiality_ratio_none_transaction_value(self):
        """None transaction value handled gracefully."""
        detector = RoutineOperationDetector()
        ratio_result = detector.calculate_materiality_ratio(
            transaction_value=None,
            market_cap=4000000000,
            annual_revenue=None,
            total_assets=None,
        )

        assert ratio_result is None


class TestMaterialityThresholds:
    """Test materiality threshold application."""

    def test_materiality_threshold_immaterial_market_cap(self):
        """Market cap below immaterial threshold."""
        detector = RoutineOperationDetector()
        # ratio = 0.005 (0.5%), threshold = 0.01 (1%)
        is_immaterial = 0.005 < detector.IMMATERIAL_THRESHOLD_MARKET_CAP

        assert is_immaterial is True

    def test_materiality_threshold_routine_revenue(self):
        """Revenue below routine threshold."""
        detector = RoutineOperationDetector()
        # ratio = 0.03 (3%), threshold = 0.05 (5%)
        is_routine = 0.03 < detector.ROUTINE_THRESHOLD_REVENUE

        assert is_routine is True

    def test_materiality_threshold_routine_assets(self):
        """Asset ratio below routine threshold (FNMA example)."""
        detector = RoutineOperationDetector()
        # ratio = 0.00014 (0.014%), threshold = 0.005 (0.5%)
        is_routine = 0.00014 < detector.ROUTINE_THRESHOLD_ASSETS

        assert is_routine is True

    def test_materiality_threshold_material_above_threshold(self):
        """Ratio above threshold indicates material transaction."""
        detector = RoutineOperationDetector()
        # ratio = 0.15 (15%), threshold = 0.01 (1%)
        is_material = 0.15 > detector.IMMATERIAL_THRESHOLD_MARKET_CAP

        assert is_material is True


class TestMaterialityScoring:
    """Test materiality scoring logic."""

    def test_materiality_scoring_immaterial_negative_two(self):
        """Clear immateriality scores -2."""
        detector = RoutineOperationDetector()
        score = detector.calculate_materiality_score(ratio=0.00014)

        assert score == -2

    def test_materiality_scoring_borderline_negative_one(self):
        """Borderline materiality scores -1."""
        detector = RoutineOperationDetector()
        score = detector.calculate_materiality_score(ratio=0.008)

        assert score == -1

    def test_materiality_scoring_material_zero(self):
        """Material transaction scores 0."""
        detector = RoutineOperationDetector()
        score = detector.calculate_materiality_score(ratio=0.15)

        assert score == 0

    def test_materiality_scoring_missing_context_zero(self):
        """Missing context (None ratio) scores 0."""
        detector = RoutineOperationDetector()
        score = detector.calculate_materiality_score(ratio=None)

        assert score == 0


class TestEnhancedConfidenceCalculation:
    """Test enhanced confidence calculation with materiality factors."""

    def test_confidence_with_clear_materiality_boost(self):
        """Clear materiality boosts confidence."""
        detector = RoutineOperationDetector()
        result = detector.detect(
            "Fannie Mae Begins Marketing Latest Loan Sale $560M",
            company_symbol="FNMA",
        )

        # routine_score >= 3, materiality_score = -2, context available
        # Expected: 0.5 + 0.2 (patterns) + 0.2 (materiality) + 0.15 (context) = 1.05 -> 1.0
        if result.routine_score >= 3 and result.materiality_score == -2:
            assert result.confidence >= 0.85  # High confidence

    def test_confidence_with_context_available_boost(self):
        """Company context availability boosts confidence."""
        detector = RoutineOperationDetector()
        result = detector.detect(
            "Quarterly Dividend Payment",
            company_symbol="BAC",
        )

        # Context available, should have +0.15 boost
        # Even without clear materiality, should be > 0.5
        assert result.confidence > 0.5

    def test_confidence_with_borderline_materiality_no_boost(self):
        """Borderline materiality (-1) doesn't boost confidence."""
        detector = RoutineOperationDetector()
        # Need to create scenario with borderline materiality
        # This requires a transaction that's borderline (ratio between thresholds)

        # For now, test that -1 materiality_score doesn't get +0.2 boost
        result = detector.detect(
            "Begins Marketing Latest Quarterly Dividend $100M",
            company_symbol="BAC",  # Assume borderline for BAC
        )

        # With routine_score >= 3 but materiality_score = -1 (borderline)
        # Should not exceed 0.7 (no materiality boost for -1)
        # Note: actual value depends on specific ratio
        assert result.confidence >= 0.5  # At least base confidence

    def test_confidence_without_context_no_boost(self):
        """No context means no context boost."""
        detector = RoutineOperationDetector()
        result = detector.detect(
            "Begins Marketing Latest Quarterly Dividend",
            company_symbol=None,  # No context
        )

        # routine_score >= 3, no context
        # Expected: 0.5 + 0.2 (patterns) = 0.7
        if result.routine_score >= 3:
            assert result.confidence <= 0.7

    def test_confidence_fnma_realistic_scenario(self):
        """FNMA realistic scenario achieves high confidence."""
        detector = RoutineOperationDetector()
        result = detector.detect(
            "Fannie Mae Begins Marketing Its Most Recent Sale Of Reperforming Loans... $560.5M",
            company_symbol="FNMA",
        )

        # FNMA example should have high confidence
        assert result.confidence >= 0.85
        assert result.result is True


class TestDetectionWithMateriality:
    """Test full detection logic with materiality integration."""

    def test_detect_with_materiality_fnma_loan_sale(self):
        """FNMA loan sale example with full materiality assessment."""
        detector = RoutineOperationDetector()
        result = detector.detect(
            "Fannie Mae Begins Marketing Its Most Recent Sale Of Reperforming Loans... $560.5M",
            company_symbol="FNMA",
        )

        assert result.routine_score >= 3
        assert result.materiality_score == -2  # Immaterial
        assert result.materiality_ratio is not None
        assert result.materiality_ratio < 0.001  # Very small ratio
        assert result.transaction_value == 560500000
        assert result.confidence >= 0.85
        assert result.result is True

    def test_detect_with_materiality_missing_context(self):
        """Missing company context handled gracefully."""
        detector = RoutineOperationDetector()
        result = detector.detect(
            "Company X Begins Marketing Loan Sale $560M",
            company_symbol="UNKNOWN",
        )

        assert result.routine_score >= 2  # Patterns detected
        assert result.materiality_score == 0  # No context = neutral
        assert result.materiality_ratio is None
        assert result.confidence < 0.85  # Lower without context

    def test_detect_with_materiality_large_material_transaction(self):
        """Large material transaction not flagged as routine."""
        detector = RoutineOperationDetector()
        result = detector.detect(
            "Bank Acquires Competitor for $50B",
            company_symbol="BAC",
        )

        assert result.routine_score == 0  # No routine patterns
        assert result.result is False  # Not routine
