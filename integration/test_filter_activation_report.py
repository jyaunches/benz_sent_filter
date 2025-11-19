"""Integration test that reports filter activation for real articles.

This test loads articles from the classified subset and runs each through
the classification API to report which filters get activated.

Filters tracked:
- is_opinion: Opinion/editorial content
- far_future_forecast: Far-future (>1 year) forecasts
- routine_operation: Routine business operations with immaterial impact

Run with: pytest integration/test_filter_activation_report.py -v -s
"""

import json
from pathlib import Path

import pytest


@pytest.mark.integration
def test_filter_activation_report(real_classifier):
    """Generate filter activation report for all articles in classified subset.

    Loads articles from 2025-08-14_to_2025-08-18_classified_subset.json and
    classifies each headline through the API to see which filters activate.
    """
    # Load the classified subset
    subset_path = Path(__file__).parent / "fixtures/2025-08-14_to_2025-08-18_classified_subset.json"

    with open(subset_path) as f:
        articles = json.load(f)

    print(f"\n{'='*80}")
    print(f"FILTER ACTIVATION REPORT - {len(articles)} articles")
    print(f"{'='*80}\n")

    # Track filter statistics
    stats = {
        "total": len(articles),
        "is_opinion": 0,
        "far_future_forecast": 0,
        "routine_operation": 0,
        "company_relevance": 0,
        "any_filter": 0,
        "no_filter": 0,
    }

    # Simple ticker to company name mapping (extracted from titles)
    ticker_to_company = {
        "FLO": "Flowers Foods",
        "XOS": "Xos",
        "BMRA": "Biomerica",
        "TGT": "Target",
        "ULTA": "Ulta Beauty",
        "DE": "Deere",
        "AI": "C3.ai",
        "NU": "Nu Holdings",
        "PINS": "Pinterest",
        "SHOP": "Shopify",
        "DASH": "DoorDash",
        "ZTS": "Zoetis",
        "ATNF": "180 Life Sciences",
        "MSFT": "Microsoft",
        "AZN": "AstraZeneca",
        "BULL": "Webull",
        "TORO": "eToro",
        "AMD": "AMD",
        "NVDA": "Nvidia",
        "XPON": "Expion360",
        "RBLX": "Roblox",
        "PANW": "Palo Alto Networks",
        "BHP": "BHP Group",
        "BTDR": "Bitdeer Technologies",
        "XP": "XP",
        "COIN": "Coinbase",
        "UAVS": "AgEagle Aerial Systems",
        "PFE": "Pfizer",
        "GNS": "Genius Group",
        "DIS": "Disney",
        "PENN": "Penn Entertainment",
        "DKNG": "DraftKings",
        "BAX": "Baxter",
        "MTCH": "Match Group",
        "DUK": "Duke Energy",
        "BHC": "Bausch Health",
        "KLTO": "Klotho Neurosciences",
        "MDT": "Medtronic",
        "HD": "Home Depot",
        "ZTO": "ZTO Express",
        "AS": "Amer Sports",
        "JHX": "James Hardie Industries",
        "VIK": "Viking Holdings",
        "ALC": "Alcon",
        "SHLS": "Shoals Technologies",
        "CNK": "Cinemark Holdings",
        "PINC": "Premier",
        "FE": "FirstEnergy",
        "STR": "Sitio Royalties",
        "VNOM": "Viper Energy",
        "META": "Meta",
        "CROX": "Crocs",
        "SERV": "Serve Robotics",
        "ILLR": "Triller",
        "ACN": "Accenture",
    }

    # Process each article
    for i, article in enumerate(articles, 1):
        eval_id = article["eval_id"]
        title = article["prompt_context"]["title"]
        ticker = article["prompt_context"]["ticker_symbols"][0] if article["prompt_context"]["ticker_symbols"] else None
        company = ticker_to_company.get(ticker) if ticker else None

        # Classify through API (with company and company_symbol for all filters)
        result = real_classifier.classify_headline(title, company=company, company_symbol=ticker)

        # Track which filters activated
        activated_filters = []

        if result.is_opinion:
            activated_filters.append("is_opinion")
            stats["is_opinion"] += 1

        if result.far_future_forecast:
            activated_filters.append(f"far_future_forecast ({result.forecast_timeframe})")
            stats["far_future_forecast"] += 1

        if result.routine_operation:
            activated_filters.append(f"routine_operation (conf={result.routine_confidence:.2f})")
            stats["routine_operation"] += 1

        # Company relevance filter: headline is NOT about the specified company
        if result.is_about_company is False:
            activated_filters.append(f"not_about_company (score={result.company_score:.2f})")
            stats["company_relevance"] += 1

        # Track overall filter activation
        if activated_filters:
            stats["any_filter"] += 1
        else:
            stats["no_filter"] += 1

        # Print article report
        print(f"{i}. {eval_id}")
        print(f"   Ticker: {ticker or 'N/A'}")
        print(f"   Title: {title}")
        print(f"   Temporal: {result.temporal_category.value}")

        if activated_filters:
            print(f"   FILTERS: {', '.join(activated_filters)}")
        else:
            print(f"   FILTERS: None")

        # Show routine operation details if available
        if result.routine_operation and result.routine_metadata:
            meta = result.routine_metadata
            print(f"   Routine Details:")
            print(f"     - Routine Score: {meta['routine_score']:.2f}")
            print(f"     - Process Stage: {meta['process_stage']}")
            if meta.get('transaction_value'):
                print(f"     - Transaction: ${meta['transaction_value']:,.0f}")
            if meta.get('materiality_ratio'):
                print(f"     - Materiality Ratio: {meta['materiality_ratio']:.4%}")

        print()

    # Print summary statistics
    print(f"{'='*80}")
    print("SUMMARY STATISTICS")
    print(f"{'='*80}")
    print(f"Total articles: {stats['total']}")
    print(f"Opinion filter: {stats['is_opinion']} ({stats['is_opinion']/stats['total']:.1%})")
    print(f"Far-future filter: {stats['far_future_forecast']} ({stats['far_future_forecast']/stats['total']:.1%})")
    print(f"Routine operation filter: {stats['routine_operation']} ({stats['routine_operation']/stats['total']:.1%})")
    print(f"Company relevance filter: {stats['company_relevance']} ({stats['company_relevance']/stats['total']:.1%})")
    print(f"\nAny filter activated: {stats['any_filter']} ({stats['any_filter']/stats['total']:.1%})")
    print(f"No filters activated: {stats['no_filter']} ({stats['no_filter']/stats['total']:.1%})")
    print(f"{'='*80}\n")

    # Test assertions to make this a valid test
    assert len(articles) == 55, f"Expected 55 articles in subset, got {len(articles)}"
    assert stats["any_filter"] + stats["no_filter"] == stats["total"], "Filter counts don't sum correctly"


@pytest.mark.integration
def test_filter_activation_by_confusion_category(real_classifier):
    """Report filter activation broken down by confusion matrix category.

    Analyzes whether filters behave differently for correct vs incorrect
    sentiment predictions.
    """
    # Load the classified subset
    subset_path = Path(__file__).parent / "fixtures/2025-08-14_to_2025-08-18_classified_subset.json"

    with open(subset_path) as f:
        articles = json.load(f)

    print(f"\n{'='*80}")
    print("FILTER ACTIVATION BY CONFUSION CATEGORY")
    print(f"{'='*80}\n")

    # Ticker to company mapping (same as main test)
    ticker_to_company = {
        "FLO": "Flowers Foods", "XOS": "Xos", "BMRA": "Biomerica", "TGT": "Target", "DE": "Deere",
        "AI": "C3.ai", "NU": "Nu Holdings", "PINS": "Pinterest", "SHOP": "Shopify", "DASH": "DoorDash",
        "ZTS": "Zoetis", "ATNF": "180 Life Sciences", "MSFT": "Microsoft", "AZN": "AstraZeneca",
        "BULL": "Webull", "AMD": "AMD", "NVDA": "Nvidia", "XPON": "Expion360", "RBLX": "Roblox",
        "PANW": "Palo Alto Networks", "BHP": "BHP Group", "BTDR": "Bitdeer Technologies", "XP": "XP",
        "COIN": "Coinbase", "UAVS": "AgEagle Aerial Systems", "PFE": "Pfizer", "GNS": "Genius Group",
        "DIS": "Disney", "PENN": "Penn Entertainment", "DKNG": "DraftKings", "BAX": "Baxter",
        "MTCH": "Match Group", "DUK": "Duke Energy", "BHC": "Bausch Health", "KLTO": "Klotho Neurosciences",
        "MDT": "Medtronic", "HD": "Home Depot", "ZTO": "ZTO Express", "AS": "Amer Sports",
        "JHX": "James Hardie Industries", "VIK": "Viking Holdings", "ALC": "Alcon",
        "SHLS": "Shoals Technologies", "CNK": "Cinemark Holdings", "PINC": "Premier",
        "FE": "FirstEnergy", "STR": "Sitio Royalties", "META": "Meta", "CROX": "Crocs",
        "SERV": "Serve Robotics", "ILLR": "Triller", "ACN": "Accenture",
    }

    # Track by confusion category
    by_category = {}

    for article in articles:
        title = article["prompt_context"]["title"]
        ticker = article["prompt_context"]["ticker_symbols"][0] if article["prompt_context"]["ticker_symbols"] else None
        company = ticker_to_company.get(ticker) if ticker else None
        confusion_cat = article["evaluation"][0]["confusion_category"]

        if confusion_cat not in by_category:
            by_category[confusion_cat] = {
                "count": 0,
                "opinion": 0,
                "far_future": 0,
                "routine": 0,
                "company_relevance": 0,
                "any_filter": 0,
            }

        # Classify
        result = real_classifier.classify_headline(title, company=company, company_symbol=ticker)

        by_category[confusion_cat]["count"] += 1

        has_filter = False
        if result.is_opinion:
            by_category[confusion_cat]["opinion"] += 1
            has_filter = True
        if result.far_future_forecast:
            by_category[confusion_cat]["far_future"] += 1
            has_filter = True
        if result.routine_operation:
            by_category[confusion_cat]["routine"] += 1
            has_filter = True
        if result.is_about_company is False:
            by_category[confusion_cat]["company_relevance"] += 1
            has_filter = True

        if has_filter:
            by_category[confusion_cat]["any_filter"] += 1

    # Print results
    for category in sorted(by_category.keys()):
        stats = by_category[category]
        count = stats["count"]

        print(f"{category}:")
        print(f"  Total: {count}")
        print(f"  Opinion: {stats['opinion']} ({stats['opinion']/count:.1%})")
        print(f"  Far-future: {stats['far_future']} ({stats['far_future']/count:.1%})")
        print(f"  Routine: {stats['routine']} ({stats['routine']/count:.1%})")
        print(f"  Company relevance: {stats['company_relevance']} ({stats['company_relevance']/count:.1%})")
        print(f"  Any filter: {stats['any_filter']} ({stats['any_filter']/count:.1%})")
        print()

    print(f"{'='*80}\n")

    # Test assertions
    assert len(by_category) > 0, "Should have at least one confusion category"
    assert sum(stats["count"] for stats in by_category.values()) == 55, "Should process all 55 articles"


@pytest.mark.integration
def test_filter_activation_by_timing_category(real_classifier):
    """Report filter activation broken down by article timing category.

    Analyzes whether filters behave differently for pre_move, during_move,
    and post_move_reporting articles.
    """
    # Load the classified subset
    subset_path = Path(__file__).parent / "fixtures/2025-08-14_to_2025-08-18_classified_subset.json"

    with open(subset_path) as f:
        articles = json.load(f)

    print(f"\n{'='*80}")
    print("FILTER ACTIVATION BY TIMING CATEGORY")
    print(f"{'='*80}\n")

    # Ticker to company mapping (same as main test)
    ticker_to_company = {
        "FLO": "Flowers Foods", "XOS": "Xos", "BMRA": "Biomerica", "TGT": "Target", "DE": "Deere",
        "AI": "C3.ai", "NU": "Nu Holdings", "PINS": "Pinterest", "SHOP": "Shopify", "DASH": "DoorDash",
        "ZTS": "Zoetis", "ATNF": "180 Life Sciences", "MSFT": "Microsoft", "AZN": "AstraZeneca",
        "BULL": "Webull", "AMD": "AMD", "NVDA": "Nvidia", "XPON": "Expion360", "RBLX": "Roblox",
        "PANW": "Palo Alto Networks", "BHP": "BHP Group", "BTDR": "Bitdeer Technologies", "XP": "XP",
        "COIN": "Coinbase", "UAVS": "AgEagle Aerial Systems", "PFE": "Pfizer", "GNS": "Genius Group",
        "DIS": "Disney", "PENN": "Penn Entertainment", "DKNG": "DraftKings", "BAX": "Baxter",
        "MTCH": "Match Group", "DUK": "Duke Energy", "BHC": "Bausch Health", "KLTO": "Klotho Neurosciences",
        "MDT": "Medtronic", "HD": "Home Depot", "ZTO": "ZTO Express", "AS": "Amer Sports",
        "JHX": "James Hardie Industries", "VIK": "Viking Holdings", "ALC": "Alcon",
        "SHLS": "Shoals Technologies", "CNK": "Cinemark Holdings", "PINC": "Premier",
        "FE": "FirstEnergy", "STR": "Sitio Royalties", "META": "Meta", "CROX": "Crocs",
        "SERV": "Serve Robotics", "ILLR": "Triller", "ACN": "Accenture",
    }

    # Track by timing category
    by_timing = {}

    for article in articles:
        title = article["prompt_context"]["title"]
        ticker = article["prompt_context"]["ticker_symbols"][0] if article["prompt_context"]["ticker_symbols"] else None
        company = ticker_to_company.get(ticker) if ticker else None
        timing_cat = article["evaluation"][0]["timing_category"]

        if timing_cat not in by_timing:
            by_timing[timing_cat] = {
                "count": 0,
                "opinion": 0,
                "far_future": 0,
                "routine": 0,
                "company_relevance": 0,
                "any_filter": 0,
            }

        # Classify
        result = real_classifier.classify_headline(title, company=company, company_symbol=ticker)

        by_timing[timing_cat]["count"] += 1

        has_filter = False
        if result.is_opinion:
            by_timing[timing_cat]["opinion"] += 1
            has_filter = True
        if result.far_future_forecast:
            by_timing[timing_cat]["far_future"] += 1
            has_filter = True
        if result.routine_operation:
            by_timing[timing_cat]["routine"] += 1
            has_filter = True
        if result.is_about_company is False:
            by_timing[timing_cat]["company_relevance"] += 1
            has_filter = True

        if has_filter:
            by_timing[timing_cat]["any_filter"] += 1

    # Print results
    for timing in sorted(by_timing.keys()):
        stats = by_timing[timing]
        count = stats["count"]

        print(f"{timing}:")
        print(f"  Total: {count}")
        print(f"  Opinion: {stats['opinion']} ({stats['opinion']/count:.1%})")
        print(f"  Far-future: {stats['far_future']} ({stats['far_future']/count:.1%})")
        print(f"  Routine: {stats['routine']} ({stats['routine']/count:.1%})")
        print(f"  Company relevance: {stats['company_relevance']} ({stats['company_relevance']/count:.1%})")
        print(f"  Any filter: {stats['any_filter']} ({stats['any_filter']/count:.1%})")
        print()

    print(f"{'='*80}\n")

    # Test assertions
    assert len(by_timing) > 0, "Should have at least one timing category"
    assert sum(stats["count"] for stats in by_timing.values()) == 55, "Should process all 55 articles"
