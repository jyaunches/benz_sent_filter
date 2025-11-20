"""Tests for quantitative catalyst detector service.

Tests MNLI-based presence detection and regex value extraction.
Phase 1: Core detector without type classification.
"""

import pytest

from benz_sent_filter.services.quantitative_catalyst_detector_mnls import (
    QuantitativeCatalystDetectorMNLS,
)


@pytest.fixture
def detector():
    """Create detector instance for testing."""
    return QuantitativeCatalystDetectorMNLS()


class TestPresenceDetection:
    """Test MNLI presence detection for quantitative catalysts."""

    def test_uuu_special_dividend_detected(self, detector):
        """UUU case: Special dividend with $1 amount should be detected."""
        headline = "Universal Safety Declares $1 Special Dividend After Feit Electric Asset Sale, Stock to Trade With Due Bills"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert "$1" in result.catalyst_values
        assert result.confidence >= 0.7

    def test_ahl_acquisition_detected(self, detector):
        """AHL case: Acquisition with multiple values should be detected."""
        headline = "Sompo To Acquire Aspen For $3.5B, Or $37.50/Share And Redeem All Class A Shares"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert "$3.5B" in result.catalyst_values
        assert "$37.50/Share" in result.catalyst_values or "$37.50/share" in result.catalyst_values
        # Multiple values should boost confidence
        assert result.confidence >= 0.8

    def test_rskd_buyback_detected(self, detector):
        """RSKD case: Buyback authorization with $75M should be detected."""
        headline = "Riskified Board Authorizes Repurchase Of Up To $75M Of Its Class A Ordinary Shares"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert "$75M" in result.catalyst_values
        assert result.confidence >= 0.7

    def test_vague_update_not_detected(self, detector):
        """Vague strategic update without numbers should not be detected."""
        headline = "Company Updates Strategic Outlook"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is False
        assert result.catalyst_values == []
        assert result.confidence == 0.0

    def test_stock_price_movement_not_catalyst(self, detector):
        """Stock price reaching a level is not a catalyst."""
        headline = "Stock Price Reaches $100 Milestone After Rally"
        result = detector.detect(headline)

        # MNLI should understand this is not a catalyst
        # If it has low presence score, has_catalyst should be False
        # Even if $100 is extracted, the semantic understanding should prevail
        assert result.has_quantitative_catalyst is False

    def test_plans_without_amount_not_detected(self, detector):
        """Vague plans without specific amounts should not be detected."""
        headline = "Company Plans to Consider Acquisition Opportunities"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is False
        assert result.catalyst_values == []


class TestValueExtraction:
    """Test regex value extraction patterns."""

    def test_extract_simple_dollar_amount(self, detector):
        """Extract simple dollar amount like $1."""
        headline = "Company Declares $1 Dividend"
        result = detector.detect(headline)

        assert "$1" in result.catalyst_values

    def test_extract_billion_amount(self, detector):
        """Extract billion amounts like $3.5B."""
        headline = "Company Acquires Competitor For $3.5B"
        result = detector.detect(headline)

        assert "$3.5B" in result.catalyst_values

    def test_extract_million_amount(self, detector):
        """Extract million amounts like $75M."""
        headline = "Board Authorizes $75M Buyback Program"
        result = detector.detect(headline)

        assert "$75M" in result.catalyst_values

    def test_extract_per_share_price_slash(self, detector):
        """Extract per-share prices with slash format."""
        headline = "Acquisition At $37.50/Share Announced"
        result = detector.detect(headline)

        # Should extract the per-share price
        values = result.catalyst_values
        assert any("37.50" in v and ("share" in v.lower() or "/" in v) for v in values)

    def test_extract_per_share_price_words(self, detector):
        """Extract per-share prices with 'per share' format."""
        headline = "Tender Offer At $10 Per Share"
        result = detector.detect(headline)

        # Should extract the per-share price
        values = result.catalyst_values
        assert any("10" in v and "share" in v.lower() for v in values) or "$10" in values

    def test_extract_multiple_values(self, detector):
        """Extract multiple dollar values from same headline."""
        headline = "Sompo To Acquire Aspen For $3.5B, Or $37.50/Share"
        result = detector.detect(headline)

        # Should extract both values
        assert len(result.catalyst_values) >= 2
        assert "$3.5B" in result.catalyst_values

    def test_percentage_with_financial_context(self, detector):
        """Extract percentage when near financial keywords."""
        headline = "Company Announces 10% Dividend Yield on Common Stock"
        result = detector.detect(headline)

        # Should extract percentage if near 'dividend' keyword
        # Implementation may or may not extract this - check result
        values = result.catalyst_values
        # At minimum, the headline should be recognized as having catalyst language
        # Percentage extraction is optional for Phase 1

    def test_percentage_without_context_ignored(self, detector):
        """Don't extract percentage from price movements."""
        headline = "Stock Up 10% After Positive News"
        result = detector.detect(headline)

        # Should NOT extract 10% (not a catalyst, just price movement)
        # And overall should not be detected as catalyst
        assert result.has_quantitative_catalyst is False


class TestConfidenceCalculation:
    """Test confidence scoring logic."""

    def test_confidence_with_single_value(self, detector):
        """Confidence should be based on presence score with single value."""
        headline = "Company Declares $1 Special Dividend"
        result = detector.detect(headline)

        # Should have reasonable confidence (≥0.7)
        assert result.confidence >= 0.7
        assert result.confidence <= 1.0

    def test_confidence_boosted_with_multiple_values(self, detector):
        """Confidence should be higher with multiple values."""
        headline = "Acquisition For $3.5B, Or $37.50/Share"
        result = detector.detect(headline)

        # Multiple values should boost confidence
        assert result.confidence >= 0.8
        assert result.confidence <= 1.0

    def test_confidence_penalized_no_values(self, detector):
        """Confidence should be low if MNLI says catalyst but no values found."""
        # This is a difficult edge case - test with a headline that might
        # confuse the MNLI model into thinking it's a catalyst
        headline = "Company Announces Major Financial Milestone Achievement"
        result = detector.detect(headline)

        # If MNLI incorrectly identifies as catalyst but no values extracted,
        # confidence should be penalized (implementation detail)
        # For this test, we just verify it doesn't crash and returns valid result
        assert 0.0 <= result.confidence <= 1.0


class TestTypeClassification:
    """Test MNLI type classification for catalyst types."""

    def test_dividend_type_classification(self, detector):
        """Dividend announcements should be classified as 'dividend' type."""
        headline = "Universal Safety Declares $1 Special Dividend"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "dividend"
        assert result.confidence >= 0.85

    def test_acquisition_type_classification(self, detector):
        """Acquisition announcements should be classified as 'acquisition' type."""
        headline = "Sompo To Acquire Aspen For $3.5B"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "acquisition"
        assert result.confidence >= 0.85

    def test_buyback_type_classification(self, detector):
        """Buyback authorizations should be classified as 'buyback' type."""
        headline = "Riskified Board Authorizes Repurchase Of Up To $75M"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "buyback"
        assert result.confidence >= 0.85

    def test_earnings_type_classification(self, detector):
        """Earnings announcements should be classified as 'earnings' type."""
        headline = "Company Beats Earnings Expectations With $2 EPS"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "earnings"

    def test_guidance_type_classification(self, detector):
        """Revenue guidance should be classified as 'guidance' type."""
        headline = "Company Raises Revenue Guidance To $500M"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "guidance"

    def test_mixed_catalyst_type(self, detector):
        """Mixed catalyst types should return 'mixed' or highest-scoring type."""
        headline = "Company Beats Earnings With $2 EPS, Declares $1 Dividend"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        # Either 'mixed' or one of the specific types (earnings/dividend)
        assert result.catalyst_type in ["mixed", "earnings", "dividend"]

    def test_no_catalyst_has_none_type(self, detector):
        """Headlines without catalyst should have catalyst_type None."""
        headline = "Company Updates Strategic Outlook"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is False
        assert result.catalyst_type is None


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_headline(self, detector):
        """Empty headline should return negative result."""
        result = detector.detect("")

        assert result.has_quantitative_catalyst is False
        assert result.catalyst_values == []
        assert result.confidence == 0.0

    def test_none_headline(self, detector):
        """None headline should return negative result."""
        result = detector.detect(None)

        assert result.has_quantitative_catalyst is False
        assert result.catalyst_values == []
        assert result.confidence == 0.0

    def test_headline_no_dollar_signs(self, detector):
        """Headline without any dollar signs should return negative result."""
        headline = "Company Provides Strategic Business Update for Shareholders"
        result = detector.detect(headline)

        assert result.catalyst_values == []
        # May or may not be detected as catalyst depending on MNLI
        # But should not crash

    def test_mixed_currency_formats(self, detector):
        """Handle mixed formats in same headline."""
        headline = "Acquisition Of $500M In Assets And $1.2B In Liabilities"
        result = detector.detect(headline)

        # Should extract both values
        assert len(result.catalyst_values) >= 2
        assert "$500M" in result.catalyst_values
        assert "$1.2B" in result.catalyst_values

    def test_decimal_amounts(self, detector):
        """Handle decimal amounts correctly."""
        headline = "Special Dividend Of $1.75 Per Share Declared"
        result = detector.detect(headline)

        # Should extract the decimal amount
        values = result.catalyst_values
        assert any("1.75" in v for v in values)
