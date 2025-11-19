"""Test company relevance filter for multi-company articles.

This test analyzes articles that mention multiple companies to see which
company gets the higher relevance score, and whether any would be filtered out.
"""

import json
from pathlib import Path

import pytest


@pytest.mark.integration
def test_company_relevance_multi_company_articles(real_classifier):
    """Test company relevance for articles mentioning multiple companies.

    For each article with multiple tickers, test relevance against ALL mentioned
    companies and report which gets the highest score.
    """
    # Load the classified subset
    subset_path = Path(__file__).parent / "fixtures/2025-08-14_to_2025-08-18_classified_subset.json"

    with open(subset_path) as f:
        articles = json.load(f)

    # Ticker to company mapping
    ticker_to_company = {
        "FLO": "Flowers Foods", "XOS": "Xos", "BMRA": "Biomerica", "TGT": "Target", "ULTA": "Ulta Beauty",
        "DE": "Deere", "AI": "C3.ai", "NU": "Nu Holdings", "PINS": "Pinterest", "SHOP": "Shopify",
        "DASH": "DoorDash", "ZTS": "Zoetis", "ATNF": "180 Life Sciences", "MSFT": "Microsoft",
        "AZN": "AstraZeneca", "BULL": "Webull", "TORO": "eToro", "AMD": "AMD", "NVDA": "Nvidia",
        "XPON": "Expion360", "RBLX": "Roblox", "PANW": "Palo Alto Networks", "BHP": "BHP Group",
        "BTDR": "Bitdeer Technologies", "XP": "XP", "COIN": "Coinbase", "UAVS": "AgEagle Aerial Systems",
        "PFE": "Pfizer", "GNS": "Genius Group", "DIS": "Disney", "PENN": "Penn Entertainment",
        "DKNG": "DraftKings", "BAX": "Baxter", "MTCH": "Match Group", "DUK": "Duke Energy",
        "BHC": "Bausch Health", "KLTO": "Klotho Neurosciences", "MDT": "Medtronic", "HD": "Home Depot",
        "ZTO": "ZTO Express", "AS": "Amer Sports", "JHX": "James Hardie Industries",
        "VIK": "Viking Holdings", "ALC": "Alcon", "SHLS": "Shoals Technologies",
        "CNK": "Cinemark Holdings", "PINC": "Premier", "FE": "FirstEnergy", "STR": "Sitio Royalties",
        "VNOM": "Viper Energy", "META": "Meta", "CROX": "Crocs", "SERV": "Serve Robotics",
        "ILLR": "Triller", "ACN": "Accenture",
    }

    print(f"\n{'='*80}")
    print("COMPANY RELEVANCE ANALYSIS - MULTI-COMPANY ARTICLES")
    print(f"{'='*80}\n")

    # Group by unique article (same title = same article, different eval_ids)
    articles_by_title = {}
    for article in articles:
        title = article["prompt_context"]["title"]
        if title not in articles_by_title:
            articles_by_title[title] = article

    # Filter to only multi-company articles
    multi_company_articles = [
        a for a in articles_by_title.values()
        if len(a["prompt_context"]["ticker_symbols"]) > 1
    ]

    print(f"Found {len(multi_company_articles)} unique multi-company articles\n")

    for i, article in enumerate(multi_company_articles, 1):
        title = article["prompt_context"]["title"]
        tickers = article["prompt_context"]["ticker_symbols"]

        print(f"{i}. ARTICLE: {title}")
        print(f"   Tickers: {', '.join(tickers)}\n")

        # Test relevance for each company
        company_scores = []
        for ticker in tickers:
            company = ticker_to_company.get(ticker)
            if not company:
                print(f"   ⚠️  No company mapping for ticker: {ticker}")
                continue

            # Classify with this company
            result = real_classifier.classify_headline(title, company=company)

            company_scores.append({
                "ticker": ticker,
                "company": company,
                "is_relevant": result.is_about_company,
                "score": result.company_score,
            })

        # Sort by score (highest first)
        company_scores.sort(key=lambda x: x["score"], reverse=True)

        # Report results
        for j, cs in enumerate(company_scores):
            marker = "✅" if cs["is_relevant"] else "❌"
            rank = "PRIMARY" if j == 0 else f"SECONDARY"

            print(f"   {marker} [{rank}] {cs['ticker']} ({cs['company']}): {cs['score']:.3f}")
            if not cs["is_relevant"]:
                print(f"      ⚠️  Would be FILTERED (score < 0.50)")

        # Summary
        relevant_count = sum(1 for cs in company_scores if cs["is_relevant"])
        print(f"\n   Summary: {relevant_count}/{len(company_scores)} companies relevant")

        if relevant_count == 0:
            print(f"   ⚠️  ENTIRE ARTICLE would be filtered (no relevant companies)")
        elif relevant_count < len(company_scores):
            print(f"   ℹ️  Partial relevance: some tickers would be filtered")

        print()

    print(f"{'='*80}\n")

    # Statistics
    total_company_checks = sum(
        len(a["prompt_context"]["ticker_symbols"])
        for a in multi_company_articles
    )

    print(f"Total unique multi-company articles: {len(multi_company_articles)}")
    print(f"Total company-article pairs tested: {total_company_checks}")

    # Test assertions
    assert len(multi_company_articles) > 0, "Should have at least one multi-company article"


@pytest.mark.integration
def test_company_relevance_edge_cases(real_classifier):
    """Test specific edge cases for company relevance detection."""

    print(f"\n{'='*80}")
    print("COMPANY RELEVANCE EDGE CASES")
    print(f"{'='*80}\n")

    edge_cases = [
        {
            "title": "Target And Ulta Beauty Shares Fall Following Termination Of Retail Partnership",
            "companies": ["Target", "Ulta Beauty"],
            "expected_behavior": "Both should be relevant (both mentioned in title)",
        },
        {
            "title": "New ESPN App to Feature Heavy Betting Integration",
            "companies": ["Disney", "ESPN"],
            "expected_behavior": "ESPN should be more relevant than parent Disney",
        },
        {
            "title": "Kevin O'Leary Says Nvidia, AMD Still Win Under Trump China Plan",
            "companies": ["Nvidia", "AMD"],
            "expected_behavior": "Both should be relevant (both mentioned)",
        },
        {
            "title": "West Penn Power Completes Electric Service Upgrades",
            "companies": ["FirstEnergy", "West Penn Power"],
            "expected_behavior": "Subsidiary may score higher than parent",
        },
    ]

    for i, case in enumerate(edge_cases, 1):
        print(f"{i}. {case['title']}")
        print(f"   Expected: {case['expected_behavior']}\n")

        for company in case["companies"]:
            result = real_classifier.classify_headline(case["title"], company=company)
            marker = "✅" if result.is_about_company else "❌"

            print(f"   {marker} {company}: {result.company_score:.3f}")

        print()

    print(f"{'='*80}\n")
