"""Tests for IMPL-030: Quantitative catalyst type disambiguation.

These tests verify that the quantitative catalyst detector correctly distinguishes
between semantically similar but directionally opposite financial events:

1. Divestiture vs Acquisition - selling assets != buying assets
2. Dilutive financing vs Dividend/Buyback - raising capital != returning capital
3. Revenue announcement vs Earnings - top-line != bottom-line

Evidence: 3 of 6 deeply-analyzed false positives in the 2025-12-29 trading-hours
evaluation had misclassified catalyst types that cascaded into wrong recipe selection
and wrong LLM predictions.

Test structure:
- TestDivestitureDisambiguation: sell/divest → NOT "acquisition"
- TestFinancingDisambiguation: securities offerings → NOT "dividend"/"buyback"
- TestRevenueDisambiguation: revenue announcements → NOT "earnings"
- TestDisambiguationPreservesCorrectClassifications: real acquisitions/dividends/earnings unchanged
- TestDisambiguationEdgeCases: tricky headlines that could cause over-correction
"""

import pytest

from benz_sent_filter.services.quantitative_catalyst_detector_mnls import (
    QuantitativeCatalystDetectorMNLS,
)


@pytest.fixture
def detector():
    """Create detector instance for testing."""
    return QuantitativeCatalystDetectorMNLS()


# ---------------------------------------------------------------------------
# 1. Divestiture vs Acquisition
# ---------------------------------------------------------------------------
class TestDivestitureDisambiguation:
    """Selling/divesting assets should NOT be classified as 'acquisition'.

    Root cause: MNLI label "This announces an acquisition or merger with a
    specific purchase price" matches sell headlines because they mention a
    purchase price. But the company is the SELLER, not the BUYER.
    """

    def test_ntrb_sell_majority_stake_not_acquisition(self, detector):
        """NTRB case: Selling only revenue source classified as 'acquisition'.

        Actual outcome: LOSER -18.9%. System predicted GAINER with 0.956 confidence.
        Nutriband sold Pocono Pharmaceutical (sole revenue source) for $5M --
        a loss vs $7.5M acquisition cost. Should not be 'acquisition'.
        """
        headline = "Nutriband to sell majority stake of Pocono Pharmaceutical for $5M"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type != "acquisition", (
            f"'sell majority stake' misclassified as acquisition (confidence={result.confidence:.3f}). "
            "Selling an asset is a divestiture, not an acquisition."
        )

    def test_divest_industrial_division(self, detector):
        """'Divest' keyword should not be classified as acquisition."""
        headline = "Company to divest industrial division for $200M"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type != "acquisition", (
            "'divest' is the opposite of 'acquire'"
        )

    def test_sells_subsidiary(self, detector):
        """'Sells subsidiary' should not be classified as acquisition."""
        headline = "Acme Corp sells pharmaceutical subsidiary for $50M"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type != "acquisition"

    def test_agrees_to_sell_business_unit(self, detector):
        """'Agrees to sell' should not be classified as acquisition."""
        headline = "GlobalTech agrees to sell its cloud business unit for $1.2B"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type != "acquisition"

    def test_disposes_of_assets(self, detector):
        """'Disposes of' should not be classified as acquisition."""
        headline = "Company disposes of real estate portfolio for $300M"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type != "acquisition"


# ---------------------------------------------------------------------------
# 2. Dilutive Financing vs Dividend/Buyback
# ---------------------------------------------------------------------------
class TestFinancingDisambiguation:
    """Securities offerings and convertible deals should NOT be classified
    as 'dividend' or 'buyback'.

    Root cause: MNLI sees "$XM" + "agreement/purchase" and maps to dividend
    or buyback because those labels also involve dollar amounts and financial
    transactions. But a securities purchase agreement is the company SELLING
    new securities (dilutive), not RETURNING capital (accretive).
    """

    def test_indp_securities_purchase_agreement_not_dividend(self, detector):
        """INDP case: $6M convertible preferred offering classified as 'dividend'.

        Actual outcome: NEUTRAL→-19.5%. System predicted GAINER with 0.85 confidence.
        Indaptus sold convertible preferred shares (111M potential shares vs 1.75M
        outstanding = 63x dilution) to a distressed-company specialist.
        """
        headline = "Indaptus Therapeutics enters $6M securities purchase agreement with David Lazar"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type not in ("dividend", "buyback"), (
            f"Securities purchase agreement misclassified as '{result.catalyst_type}'. "
            "This is dilutive financing (company selling new securities), not a dividend/buyback."
        )

    def test_convertible_note_offering_not_dividend(self, detector):
        """Convertible note offering is dilutive financing, not dividend."""
        headline = "Company announces $10M convertible note offering"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type not in ("dividend", "buyback"), (
            "Convertible notes are debt that converts to equity (dilutive), not a dividend"
        )

    def test_private_placement_not_dividend(self, detector):
        """Private placement is equity issuance, not dividend."""
        headline = "Company closes $25M private placement of common stock"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type not in ("dividend", "buyback")

    def test_preferred_stock_offering_not_dividend(self, detector):
        """Preferred stock offering is capital raise, not dividend."""
        headline = "Company prices $50M preferred stock offering at $25 per share"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type != "dividend", (
            "Selling preferred stock is a capital raise, not returning capital via dividend"
        )

    def test_atm_facility_not_buyback(self, detector):
        """At-the-market equity facility is share issuance, not buyback."""
        headline = "Company enters $100M at-the-market equity offering agreement"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type != "buyback", (
            "ATM offering is selling shares into market (dilution), not buying them back"
        )


# ---------------------------------------------------------------------------
# 3. Revenue Announcement vs Earnings
# ---------------------------------------------------------------------------
class TestRevenueDisambiguation:
    """Revenue/client announcements should NOT be classified as 'earnings'.

    Root cause: MNLI sees "$XK" + "revenue" and maps to "earnings" because
    the earnings label says "earnings results with specific dollar figures"
    and revenue is semantically close to earnings. But revenue != profit.
    A company can announce growing revenue while remaining deeply unprofitable.
    """

    def test_onar_recurring_revenue_not_earnings(self, detector):
        """ONAR case: $400K recurring revenue classified as 'earnings'.

        Actual outcome: NEUTRAL→-35.1%. System predicted GAINER with 0.85 confidence.
        ONAR is a sub-penny OTC stock ($0.0232). $400K in new client revenue
        is not an earnings result -- the company has persistent losses.
        """
        headline = "Onar says new December clients add over $400,000 in recurring revenue"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type != "earnings", (
            f"Revenue announcement misclassified as 'earnings' (confidence={result.confidence:.3f}). "
            "Recurring revenue from new clients is top-line, not earnings/profit."
        )

    def test_contract_revenue_not_earnings(self, detector):
        """New contract revenue is top-line, not earnings."""
        headline = "Company reports $50M in new contract revenue for Q4"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type != "earnings", (
            "Contract revenue is top-line growth, not earnings results"
        )

    def test_subscription_revenue_growth_not_earnings(self, detector):
        """Subscription revenue growth is not earnings."""
        headline = "SaaS company adds $2M in annual recurring subscription revenue"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type != "earnings"

    def test_booking_revenue_not_earnings(self, detector):
        """Revenue bookings are not earnings."""
        headline = "Company announces $15M in new booking revenue from enterprise clients"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type != "earnings"


# ---------------------------------------------------------------------------
# 4. Preserve Correct Classifications (Do Not Over-Correct)
# ---------------------------------------------------------------------------
class TestDisambiguationPreservesCorrectClassifications:
    """Ensure disambiguation does NOT break correctly classified catalysts.

    These tests use the same headlines from the existing test suite plus
    additional clear-cut cases. They must continue to pass after IMPL-030.
    """

    def test_real_acquisition_still_classified_correctly(self, detector):
        """'Acquires' with purchase price should remain 'acquisition'."""
        headline = "Sompo To Acquire Aspen For $3.5B, Or $37.50/Share"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "acquisition"
        assert result.confidence >= 0.85

    def test_real_acquisition_with_agrees_to_acquire(self, detector):
        """'Agrees to acquire' should remain 'acquisition'."""
        headline = "Company agrees to acquire competitor for $500M in all-cash deal"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "acquisition"

    def test_real_dividend_still_classified_correctly(self, detector):
        """'Declares dividend' with per-share amount should remain 'dividend'."""
        headline = "Universal Safety Declares $1 Special Dividend"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "dividend"
        assert result.confidence >= 0.85

    def test_real_dividend_per_share(self, detector):
        """Per-share dividend should remain 'dividend'."""
        headline = "Company declares $0.50 per share quarterly dividend"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "dividend"

    def test_real_buyback_still_classified_correctly(self, detector):
        """'Authorizes repurchase' should remain 'buyback'."""
        headline = "Riskified Board Authorizes Repurchase Of Up To $75M"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "buyback"
        assert result.confidence >= 0.85

    def test_real_earnings_still_classified_correctly(self, detector):
        """'Beats earnings' with EPS should remain 'earnings'."""
        headline = "Company Beats Earnings Expectations With $2 EPS"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "earnings"

    def test_real_earnings_with_net_income(self, detector):
        """Net income announcement should remain 'earnings'."""
        headline = "Company reports net income of $150M, up 25% year over year"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "earnings"

    def test_real_guidance_still_classified_correctly(self, detector):
        """Revenue guidance should remain 'guidance'."""
        headline = "Company Raises Revenue Guidance To $500M"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "guidance"


# ---------------------------------------------------------------------------
# 5. Edge Cases - Headlines That Could Cause Over-Correction
# ---------------------------------------------------------------------------
class TestDisambiguationEdgeCases:
    """Tricky headlines where naive keyword matching could over-correct.

    These test that the disambiguation is precise enough to not
    swing too far in the opposite direction.
    """

    def test_sell_in_acquisition_context_is_still_acquisition(self, detector):
        """'Sells products' in revenue context is not a divestiture.

        'Sell' here means product sales, not asset divestiture.
        Should not trigger divestiture disambiguation.
        """
        headline = "Company sells $5M worth of new product in first week of launch"
        result = detector.detect(headline)

        # This is a revenue/product sales headline, not a divestiture
        # The key is it should NOT be classified as "acquisition" either
        if result.has_quantitative_catalyst:
            assert result.catalyst_type != "acquisition"

    def test_sale_of_shares_to_fund_acquisition(self, detector):
        """Headline mentioning both selling and acquiring.

        When the headline is primarily about an acquisition funded by a sale,
        the dominant catalyst is the acquisition.
        """
        headline = "Company to acquire rival for $200M, funded by sale of non-core assets"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        # The dominant financial event is the acquisition
        assert result.catalyst_type == "acquisition"

    def test_definitive_agreement_to_acquire_not_confused_by_agreement(self, detector):
        """'Agreement' in acquisition context should remain 'acquisition'.

        The word 'agreement' appears in both 'securities purchase agreement'
        (financing) and 'definitive agreement to acquire' (acquisition).
        Disambiguation should not trigger on acquisition agreements.
        """
        headline = "Company enters definitive agreement to acquire competitor for $100M"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "acquisition"

    def test_merger_agreement_not_confused_with_financing(self, detector):
        """Merger agreement should be 'acquisition', not financing."""
        headline = "Company signs $800M merger agreement with industry peer"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "acquisition"

    def test_purchase_price_in_acquisition_not_confused_with_financing(self, detector):
        """'Purchase' in acquisition context is not 'securities purchase'."""
        headline = "Tech giant announces $2B purchase of AI startup"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "acquisition"

    def test_revenue_in_earnings_headline_still_earnings(self, detector):
        """'Revenue' mentioned alongside earnings metrics is still 'earnings'.

        Disambiguation should not trigger when revenue appears as part of
        a full earnings report (alongside EPS, net income, etc.).
        """
        headline = "Company reports Q4 earnings: revenue $100M, EPS $1.50, net income $15M"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        # With EPS and net income present, this is genuinely earnings
        assert result.catalyst_type == "earnings"

    def test_stock_sale_insider_not_divestiture(self, detector):
        """Insider stock sale is not an asset divestiture.

        This is an insider transaction, not a corporate divestiture.
        The system may not detect this as a catalyst at all (correct),
        or may classify it -- but it should not be 'acquisition'.
        """
        headline = "CEO sells $3M worth of company stock in planned transaction"
        result = detector.detect(headline)

        # This is not a corporate catalyst, probably won't be detected
        # But if it is, it should not be 'acquisition'
        if result.has_quantitative_catalyst:
            assert result.catalyst_type != "acquisition"

    def test_dividend_reinvestment_plan_is_dividend(self, detector):
        """Dividend reinvestment is still fundamentally a 'dividend'."""
        headline = "Company announces $2 special dividend with reinvestment option"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "dividend"

    def test_share_repurchase_via_tender_is_buyback(self, detector):
        """Tender offer for share repurchase is still 'buyback'."""
        headline = "Company launches $50M tender offer to repurchase shares at $25 per share"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type == "buyback"

    def test_secondary_offering_not_buyback(self, detector):
        """Secondary offering is share issuance, not buyback.

        A secondary offering increases share count (dilutive),
        while a buyback decreases it. These are opposites.
        """
        headline = "Company prices $150M secondary offering of 10M shares"
        result = detector.detect(headline)

        assert result.has_quantitative_catalyst is True
        assert result.catalyst_type != "buyback", (
            "Secondary offering is share ISSUANCE (dilutive), not REPURCHASE"
        )
