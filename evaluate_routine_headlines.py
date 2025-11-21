"""Evaluate routine operation filter on borderline headlines.

This script tests headlines that were classified as NOT routine but feel like
they should be routine operations, to identify tuning opportunities.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from benz_sent_filter.services.routine_detector_mnls import RoutineOperationDetectorMNLS

# Test headlines from benz_evaluator that feel routine but were classified as not routine
test_cases = [
    {
        "headline": "McDonald's And DoorDash Launch New Direct Online Ordering For McDelivery With No App Or Account Needed",
        "symbols": ["DASH", "MCD"],
        "expected_routine": "Maybe - product launch, but routine for large companies",
    },
    {
        "headline": "Alaska Airlines, Bank of America Launch $395 Atmos Summit Card Packed With Travel Perks",
        "symbols": ["ALK", "BAC"],
        "expected_routine": "Yes - credit card launches are routine for BAC",
    },
    {
        "headline": "Progressive Reports July Results: Net Income Up 34% To $1.09B, EPS $1.85; Net Premiums Written +11%, Combined Ratio Improves To 85.3",
        "symbols": ["PGR"],
        "expected_routine": "Yes - monthly periodic reporting",
    },
    {
        "headline": "Sempra And ConocoPhillips Sign 20-Year Sale And Purchase Agreement For 4 Million Tonnes Per Annum Of LNG Offtake From Port Arthur LNG Phase 2 Development Project In Jefferson County, TX",
        "symbols": ["COP", "SRE"],
        "expected_routine": "No - major contract, material",
    },
    {
        "headline": "Vornado Realty Trust To Purchase 623 Fifth Avenue Office Condominium For $218M",
        "symbols": ["VNO"],
        "expected_routine": "Yes - real estate purchases are routine for REITs",
    },
    {
        "headline": "Zillow Signs Agreements With Morgan Stanley, Citi, Barclays, And JPMorgan To Terminate Capped Call Transactions, Receiving $38.2M And 3.1M Class C Shares",
        "symbols": ["Z", "ZG"],
        "expected_routine": "Maybe - financial restructuring",
    },
    {
        "headline": "SLB's OneSubsea JV Wins EPC Contract From Equinor For 12-Well All-Electric Subsea Production System In The Fram Sør Field, Offshore Norway",
        "symbols": ["EQNR", "SLB"],
        "expected_routine": "Maybe - contract wins routine for large industrial",
    },
    {
        "headline": "Eli Lilly Announced Topline Results Phase 3 MonarchE Trial. Treatment With Two Years Of Verzenio Plus Endocrine Therapy (ET) Demonstrated A Statistically Significant And Clinically Meaningful Improvement In Overall Survival Compared To ET For Hormone Receptor Positive, HER2-, Node-positive, High-risk Early Breast Cancer",
        "symbols": ["LLY"],
        "expected_routine": "No - clinical trial results are material for pharma",
    },
    {
        "headline": "Royalty Pharma To Provide Up To $300M In Funding To Zenas BioPharma In Exchange For Royalty On Sales Of Obexelimab",
        "symbols": ["RPRX", "ZBIO"],
        "expected_routine": "Maybe - investment deals, depends on size",
    },
]


def main():
    """Run evaluation on test headlines."""
    print("=" * 80)
    print("ROUTINE OPERATIONS FILTER EVALUATION")
    print("=" * 80)
    print()

    detector = RoutineOperationDetectorMNLS()

    for i, case in enumerate(test_cases, 1):
        headline = case["headline"]
        symbols = case["symbols"]
        expected = case["expected_routine"]

        print(f"\n{i}. {headline[:70]}...")
        print(f"   Symbols: {', '.join(symbols)}")
        print(f"   Expected: {expected}")
        print("-" * 80)

        # Test without company symbol first
        result_no_company = detector.detect(headline, company_symbol=None)
        print(f"   Without company context:")
        print(f"     MNLS Score: {result_no_company.routine_score:.3f}")
        print(f"     Classification: {'ROUTINE' if result_no_company.result else 'NOT ROUTINE'}")
        print(f"     Process Stage: {result_no_company.process_stage}")
        print(f"     Transaction Value: ${result_no_company.transaction_value:,.0f}" if result_no_company.transaction_value else "     Transaction Value: None")

        # Test with each company symbol
        for symbol in symbols:
            result = detector.detect(headline, company_symbol=symbol)
            print(f"\n   With {symbol} context:")
            print(f"     MNLS Score: {result.routine_score:.3f}")
            print(f"     Classification: {'ROUTINE' if result.result else 'NOT ROUTINE'}")
            if result.materiality_score is not None:
                print(f"     Materiality Score: {result.materiality_score}")
                if result.materiality_ratio is not None:
                    print(f"     Materiality Ratio: {result.materiality_ratio:.4f} ({result.materiality_ratio*100:.2f}%)")
            else:
                print(f"     Materiality: No context available for {symbol}")

        print()


if __name__ == "__main__":
    main()
