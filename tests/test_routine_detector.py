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
