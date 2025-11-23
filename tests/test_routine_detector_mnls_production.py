"""
Comprehensive test suite for MNLS-based routine operations detector.

This file consolidates all routine/material classification tests in one place:
1. Production regression tests (benz_sent_filter-3746) - material events misclassified as routine
2. Routine operation examples - should be classified as routine
3. Edge cases and boundary conditions

The goal is to have a complete picture of what the detector should and shouldn't
flag as routine operations.
"""

import pytest

from benz_sent_filter.services.routine_detector_mnls import (
    RoutineOperationDetectorMNLS,
)


@pytest.fixture
def detector():
    """Create a fresh detector instance for each test.

    This ensures the MNLI pipeline is reset between tests to avoid
    state leakage that can cause intermittent failures in the full suite.
    """
    return RoutineOperationDetectorMNLS()


class TestProductionMaterialEventsNotRoutine:
    """Test that clearly material events are NOT classified as routine.

    These are regression tests based on actual production failures where
    material events ($23B sales, $180M offerings, etc.) were incorrectly
    marked as routine operations.
    """

    def test_echostar_23b_spectrum_sale_not_routine(self, detector):
        """$23B spectrum license sale should be material, not routine.

        Article: benzinga_47327444_SATS
        Tickers: SATS, T
        Issue: Incorrectly classified as routine after GENERAL_TOPIC fix
        """
        headline = (
            "EchoStar To Sell 3.45 GHz And 600 MHz Spectrum Licenses To AT&T For $23B, "
            "Establishes Hybrid MNO Agreement With Boost Mobile To Address FCC Inquiries"
        )

        result = detector.detect(headline)

        # $23B transaction is material, not routine
        assert result.result is False, (
            f"$23B spectrum sale should be MATERIAL, not routine. "
            f"Got routine_operation={result.result}, confidence={result.confidence:.2f}"
        )
        # Confidence should be low for routine classification
        assert result.confidence < 0.5, (
            f"Routine confidence should be low (<0.5) for $23B sale. "
            f"Got {result.confidence:.2f}"
        )

    def test_nuscale_power_agreement_not_routine(self, detector):
        """Major 6 GW deployment agreement should be material, not routine.

        Article: benzinga_47469914_SMR
        Tickers: SMR
        Issue: Incorrectly classified as routine after GENERAL_TOPIC fix
        """
        headline = (
            "NuScale Power Supports ENTRA1 Energy's Agreement With Tennessee Valley Authority "
            "To Deploy Up To 6 Gigawatts Of NuScale SMR Capacity Across TVA's Seven-State Service Region"
        )

        result = detector.detect(headline)

        # Major multi-gigawatt deployment agreement is material
        assert result.result is False, (
            f"6 GW deployment agreement should be MATERIAL, not routine. "
            f"Got routine_operation={result.result}, confidence={result.confidence:.2f}"
        )

    def test_airnet_180m_offering_not_routine(self, detector):
        """$180M capital raise should be material, not routine.

        Article: benzinga_47279040_ANTE
        Tickers: ANTE
        Issue: Incorrectly classified as routine after GENERAL_TOPIC fix
        """
        headline = (
            "AirNet Technology Enters Registered Direct Offering For Sale Of 80,826,225 "
            "Ordinary Shares And Accompanying Warrants At Combined Purchase Price Of $2.227; "
            "Gross Proceeds $180M"
        )

        result = detector.detect(headline)

        # $180M capital raise is material, not routine
        assert result.result is False, (
            f"$180M capital raise should be MATERIAL, not routine. "
            f"Got routine_operation={result.result}, confidence={result.confidence:.2f}"
        )
        assert result.confidence < 0.5, (
            f"Routine confidence should be low (<0.5) for $180M offering. "
            f"Got {result.confidence:.2f}"
        )

    def test_lantronix_defense_contract_not_routine(self, detector):
        """Military drone program selection should be material, not routine.

        Article: benzinga_47181720_RCAT
        Tickers: LTRX, RCAT
        Note: While this doesn't have a specific dollar amount, being selected for
        a U.S. Army program is a significant strategic win.
        """
        headline = (
            "Lantronix's TAA- And NDAA-Compliant Solution Selected By Teal Drones For "
            "Production Of Black Widow Drones Under U.S. Army's Short-Range Reconnaissance Program"
        )

        result = detector.detect(headline)

        # U.S. Army program selection is material
        assert result.result is False, (
            f"U.S. Army program selection should be MATERIAL, not routine. "
            f"Got routine_operation={result.result}, confidence={result.confidence:.2f}"
        )

    def test_immunitybio_clinical_trial_results_not_routine(self, detector):
        """Positive clinical trial results (complete responses) should be material.

        Article: benzinga_47088121_IBRX
        Tickers: IBRX
        Note: Clinical trial results showing complete responses are significant events
        for biotech companies.
        """
        headline = (
            "ImmunityBio Announces Early QUILT-106 Phase I Data Showing Complete Responses "
            "In Waldenstrom Macroglobulinemia Patients Treated With CD19 CAR-NK Therapy"
        )

        result = detector.detect(headline)

        # Clinical trial complete responses are material
        assert result.result is False, (
            f"Clinical trial complete responses should be MATERIAL, not routine. "
            f"Got routine_operation={result.result}, confidence={result.confidence:.2f}"
        )


class TestRoutineDetectorTransactionExtraction:
    """Test that transaction values are correctly extracted."""

    def test_extract_23b_from_echostar_headline(self, detector):
        """Should extract $23B from spectrum sale headline."""
        headline = (
            "EchoStar To Sell 3.45 GHz And 600 MHz Spectrum Licenses To AT&T For $23B, "
            "Establishes Hybrid MNO Agreement With Boost Mobile To Address FCC Inquiries"
        )

        result = detector.detect(headline)

        assert result.transaction_value is not None, "Should extract transaction value"
        assert result.transaction_value == 23_000_000_000, (
            f"Should extract $23B (23000000000). Got {result.transaction_value}"
        )

    def test_extract_180m_from_airnet_headline(self, detector):
        """Should extract $180M from offering headline."""
        headline = (
            "AirNet Technology Enters Registered Direct Offering For Sale Of 80,826,225 "
            "Ordinary Shares And Accompanying Warrants At Combined Purchase Price Of $2.227; "
            "Gross Proceeds $180M"
        )

        result = detector.detect(headline)

        assert result.transaction_value is not None, "Should extract transaction value"
        assert result.transaction_value == 180_000_000, (
            f"Should extract $180M (180000000). Got {result.transaction_value}"
        )


class TestRoutineOperationsShouldBeRoutine:
    """Test that actual routine operations ARE classified as routine.

    These are examples of routine business activities that should be filtered:
    - Quarterly dividends
    - Regular buyback programs
    - Routine SEC filings
    - Standard loan portfolio sales (for financial institutions)
    """

    def test_quarterly_dividend_is_routine(self, detector):
        """Quarterly dividend should be routine for established companies."""
        headline = "Bank announces quarterly dividend payment"

        result = detector.detect(headline)

        # Quarterly dividend is routine
        assert result.result is True, (
            f"Quarterly dividend should be ROUTINE. "
            f"Got routine_operation={result.result}, confidence={result.confidence:.2f}"
        )

    def test_sec_filing_is_routine(self, detector):
        """Routine SEC filing should be classified as routine."""
        headline = "Bank files quarterly MBS disclosure report with SEC"

        result = detector.detect(headline)

        # SEC filing is routine
        assert result.result is True, (
            f"SEC filing should be ROUTINE. "
            f"Got routine_operation={result.result}, confidence={result.confidence:.2f}"
        )

    def test_fnma_loan_sale_560m_is_routine_for_fnma(self, detector):
        """$560M loan sale is routine for FNMA given its $4T asset base.

        Example from test_api.py
        FNMA context: $4T assets, so $560M is 0.014% of assets (immaterial)
        """
        headline = (
            "Fannie Mae Begins Marketing Its Most Recent Sale Of Reperforming Loans; "
            "Sale Consists Of ~ 3,058 Loans, Having An Unpaid Principal Balance Of ~ $560.5M"
        )

        result = detector.detect(headline, company_symbol="FNMA")

        # With FNMA context, this should be routine due to materiality threshold
        # $560M / $4T assets = 0.014% << 0.5% threshold
        assert result.result is True, (
            f"$560M loan sale should be ROUTINE for FNMA ($4T assets). "
            f"Got routine_operation={result.result}, confidence={result.confidence:.2f}, "
            f"materiality_ratio={result.materiality_ratio}"
        )


# ============================================================================
# COMPREHENSIVE SUMMARY - All Test Cases
# ============================================================================
"""
MATERIAL EVENTS (should NOT be routine):
========================================

1. Large Transactions (>$1B):
   - EchoStar $23B spectrum sale → Currently FAILING (51% routine)
   - Major financial impact, transformational deals

2. Strategic Partnerships & Agreements:
   - NuScale 6 GW deployment agreement → Currently FAILING (56% routine)
   - Lantronix U.S. Army program selection → Currently FAILING (68% routine)
   - Large-scale deployments, government contracts

3. Capital Raises (>$100M):
   - AirNet $180M offering → Currently FAILING (53% routine)
   - Significant dilution events, major capital events

4. Clinical Trial Results:
   - ImmunityBio complete responses → Currently FAILING (67% routine)
   - Biotech value drivers, regulatory milestones

ROUTINE OPERATIONS (should BE routine):
========================================

1. Recurring Payments:
   - Quarterly dividends → Expected to pass
   - Regular buyback programs → Expected to pass

2. Administrative Actions:
   - SEC filings, disclosure reports → Expected to pass
   - Routine compliance activities → Expected to pass

3. Immaterial Transactions (relative to company size):
   - FNMA $560M loan sale (0.014% of $4T assets) → Expected to pass
   - Small relative to company's normal operations

CURRENT PROBLEM:
================
The MNLI labels "transformational change" vs "incremental progress" are failing
to distinguish between:
- Multi-billion dollar strategic transactions (material)
- Routine quarterly activities (routine)

The model sees both as "incremental progress" with 50-70% confidence.

PROPOSED SOLUTIONS:
===================
1. Improve MNLI labels to focus on investor materiality
2. Add pre-filtering for large transactions (>$100M automatically material)
3. Better incorporate transaction value into final classification
"""
