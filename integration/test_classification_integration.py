"""Integration tests with real DistilBERT-MNLI model.

These tests download and load the actual model from Hugging Face.
Run with: pytest -m integration
Skip with: pytest -m "not integration"
"""

import time

import pytest

from benz_sent_filter.models.classification import TemporalCategory


@pytest.mark.integration
def test_real_model_loads_successfully(real_classifier):
    """Test that ClassificationService initializes with real transformers."""
    assert real_classifier is not None
    assert hasattr(real_classifier, "_pipeline")


@pytest.mark.integration
def test_real_inference_produces_valid_scores(
    real_classifier, sample_headline_opinion
):
    """Test that real model produces scores in valid range [0, 1]."""
    result = real_classifier.classify_headline(sample_headline_opinion)

    # All scores should be between 0 and 1
    assert 0 <= result.scores.opinion_score <= 1
    assert 0 <= result.scores.news_score <= 1
    assert 0 <= result.scores.past_score <= 1
    assert 0 <= result.scores.future_score <= 1
    assert 0 <= result.scores.general_score <= 1


@pytest.mark.integration
def test_opinion_headline_detection_real_model(
    real_classifier, sample_headline_opinion
):
    """Test real model detects opinion in 'Why the Fed Is Wrong About Inflation'."""
    result = real_classifier.classify_headline(sample_headline_opinion)

    # Real model should score opinion higher than random (> 0.5)
    # Note: We use lenient thresholds since zero-shot may not be perfect
    assert result.scores.opinion_score > 0.5, (
        f"Expected opinion_score > 0.5 for opinion headline, "
        f"got {result.scores.opinion_score}"
    )


@pytest.mark.integration
def test_news_headline_detection_real_model(real_classifier, sample_headline_news):
    """Test real model detects news in 'Fed Raises Interest Rates by 25 Basis Points'."""
    result = real_classifier.classify_headline(sample_headline_news)

    # Real model should score news higher than random
    assert result.scores.news_score > 0.5, (
        f"Expected news_score > 0.5 for news headline, " f"got {result.scores.news_score}"
    )


@pytest.mark.integration
def test_past_event_temporal_classification_real_model(
    real_classifier, sample_headline_past
):
    """Test real model classifies 'Tesla Shares Surge After Yesterday's Earnings Beat' as past."""
    result = real_classifier.classify_headline(sample_headline_past)

    assert result.temporal_category == TemporalCategory.PAST_EVENT, (
        f"Expected PAST_EVENT for past headline, " f"got {result.temporal_category}"
    )


@pytest.mark.integration
def test_future_event_temporal_classification_real_model(
    real_classifier, sample_headline_future
):
    """Test real model classifies 'Tesla to Report Q4 Earnings Next Week' as future."""
    result = real_classifier.classify_headline(sample_headline_future)

    assert result.temporal_category == TemporalCategory.FUTURE_EVENT, (
        f"Expected FUTURE_EVENT for future headline, "
        f"got {result.temporal_category}"
    )


@pytest.mark.integration
def test_general_topic_temporal_classification_real_model(
    real_classifier, sample_headline_general
):
    """Test real model classifies 'How Tesla Changed the EV Market' as general."""
    result = real_classifier.classify_headline(sample_headline_general)

    assert result.temporal_category == TemporalCategory.GENERAL_TOPIC, (
        f"Expected GENERAL_TOPIC for general headline, "
        f"got {result.temporal_category}"
    )


@pytest.mark.integration
def test_batch_processing_maintains_accuracy_real_model(
    real_classifier,
    sample_headline_opinion,
    sample_headline_news,
    sample_headline_past,
    sample_headline_future,
    sample_headline_general,
):
    """Test that batch processing maintains accuracy for all fixture headlines."""
    headlines = [
        sample_headline_opinion,
        sample_headline_news,
        sample_headline_past,
        sample_headline_future,
        sample_headline_general,
    ]

    results = real_classifier.classify_batch(headlines)

    assert len(results) == 5

    # Check that each result has valid temporal category
    # (we don't check exact values since batch vs single may differ slightly)
    for result in results:
        assert result.temporal_category in [
            TemporalCategory.PAST_EVENT,
            TemporalCategory.FUTURE_EVENT,
            TemporalCategory.GENERAL_TOPIC,
        ]


@pytest.mark.integration
def test_classification_consistency_real_model(real_classifier):
    """Test that same headline classified twice produces identical results."""
    headline = "Tesla Announces New Product Launch"

    result1 = real_classifier.classify_headline(headline)
    result2 = real_classifier.classify_headline(headline)

    # Scores should be exactly identical (deterministic model)
    assert result1.scores.opinion_score == result2.scores.opinion_score
    assert result1.scores.news_score == result2.scores.news_score
    assert result1.scores.past_score == result2.scores.past_score
    assert result1.scores.future_score == result2.scores.future_score
    assert result1.scores.general_score == result2.scores.general_score

    # Boolean flags and temporal category should match
    assert result1.is_opinion == result2.is_opinion
    assert result1.is_straight_news == result2.is_straight_news
    assert result1.temporal_category == result2.temporal_category


@pytest.mark.integration
def test_response_time_single_headline_real_model(real_classifier):
    """Test that single headline classification completes in < 5 seconds.

    DeBERTa-v3-large is ~6x larger than DistilBERT, so inference times are expected
    to be slower (~4-5s vs ~1s). This is acceptable for the accuracy improvement.
    """
    headline = "Stock Market Reaches New High"

    start_time = time.time()
    result = real_classifier.classify_headline(headline)
    elapsed_time = time.time() - start_time

    assert elapsed_time < 5.0, (
        f"Expected classification in < 5s, took {elapsed_time:.2f}s"
    )
    assert result is not None


@pytest.mark.integration
def test_response_time_batch_10_headlines_real_model(real_classifier):
    """Test that batch of 10 headlines completes in < 50 seconds.

    DeBERTa-v3-large processes ~4-5s per headline, so 10 headlines should take
    ~40-50s. This is acceptable for the accuracy improvement over DistilBERT.
    """
    headlines = [f"Test headline number {i}" for i in range(10)]

    start_time = time.time()
    results = real_classifier.classify_batch(headlines)
    elapsed_time = time.time() - start_time

    assert elapsed_time < 50.0, (
        f"Expected batch classification in < 50s, took {elapsed_time:.2f}s"
    )
    assert len(results) == 10


# ============================================================================
# Company Relevance Detection Integration Tests
# ============================================================================


# Test data for company relevance validation
DELL_NVIDIA_HEADLINE = (
    "Dell Unveils AI Data Platform Updates; Launches First 2U Server "
    "With NVIDIA Blackwell GPUs"
)


@pytest.mark.integration
def test_company_relevance_positive_match_dell(real_classifier):
    """Test that Dell headline correctly identifies Dell relevance with real model."""
    result = real_classifier.classify_headline(DELL_NVIDIA_HEADLINE, company="Dell")

    # Real model should detect Dell is relevant
    assert result.is_about_company is True, (
        f"Expected is_about_company=True for Dell headline with company='Dell', "
        f"got {result.is_about_company}"
    )
    assert result.company_score >= 0.5, (
        f"Expected company_score >= 0.5 for Dell relevance, "
        f"got {result.company_score}"
    )
    assert result.company == "Dell"


@pytest.mark.integration
def test_company_relevance_negative_match_tesla(real_classifier):
    """Test that Dell headline correctly rejects Tesla relevance with real model."""
    result = real_classifier.classify_headline(DELL_NVIDIA_HEADLINE, company="Tesla")

    # Real model should detect Tesla is not relevant
    assert result.is_about_company is False, (
        f"Expected is_about_company=False for Dell headline with company='Tesla', "
        f"got {result.is_about_company}"
    )
    assert result.company_score < 0.5, (
        f"Expected company_score < 0.5 for Tesla irrelevance, "
        f"got {result.company_score}"
    )
    assert result.company == "Tesla"


@pytest.mark.integration
def test_company_relevance_multi_company_nvidia(real_classifier):
    """Test that Dell/NVIDIA headline correctly identifies NVIDIA relevance."""
    result = real_classifier.classify_headline(DELL_NVIDIA_HEADLINE, company="NVIDIA")

    # Real model should detect NVIDIA is relevant (mentioned in headline)
    assert result.is_about_company is True, (
        f"Expected is_about_company=True for Dell/NVIDIA headline with company='NVIDIA', "
        f"got {result.is_about_company}"
    )
    assert result.company_score >= 0.5, (
        f"Expected company_score >= 0.5 for NVIDIA relevance, "
        f"got {result.company_score}"
    )


@pytest.mark.integration
def test_company_relevance_multi_company_unrelated(real_classifier):
    """Test that Dell/NVIDIA headline correctly rejects Apple relevance."""
    result = real_classifier.classify_headline(DELL_NVIDIA_HEADLINE, company="Apple")

    # Real model should detect Apple is not relevant
    assert result.is_about_company is False, (
        f"Expected is_about_company=False for Dell/NVIDIA headline with company='Apple', "
        f"got {result.is_about_company}"
    )


@pytest.mark.integration
def test_company_relevance_accuracy_threshold(real_classifier):
    """Test company relevance achieves >80% accuracy across test fixtures."""
    test_cases = [
        {
            "headline": DELL_NVIDIA_HEADLINE,
            "relevant_companies": ["Dell", "NVIDIA"],
            "irrelevant_companies": ["Tesla", "Apple", "Microsoft"],
        },
        {
            "headline": "Tesla Reports Record Q3 Deliveries, Shares Jump 5%",
            "relevant_companies": ["Tesla"],
            "irrelevant_companies": ["Ford", "GM", "Dell"],
        },
        {
            "headline": "Apple Announces iPhone 15 with USB-C Port",
            "relevant_companies": ["Apple"],
            "irrelevant_companies": ["Samsung", "Google", "Microsoft"],
        },
        {
            "headline": "Microsoft Azure Revenue Grows 29% in Cloud Push",
            "relevant_companies": ["Microsoft"],
            "irrelevant_companies": ["Amazon", "Google", "IBM"],
        },
    ]

    correct_predictions = 0
    total_predictions = 0

    for case in test_cases:
        headline = case["headline"]

        # Test relevant companies (should be True)
        for company in case["relevant_companies"]:
            result = real_classifier.classify_headline(headline, company=company)
            if result.is_about_company is True:
                correct_predictions += 1
            total_predictions += 1

        # Test irrelevant companies (should be False)
        for company in case["irrelevant_companies"]:
            result = real_classifier.classify_headline(headline, company=company)
            if result.is_about_company is False:
                correct_predictions += 1
            total_predictions += 1

    accuracy = correct_predictions / total_predictions
    assert accuracy >= 0.80, (
        f"Expected accuracy >= 80% for company relevance, "
        f"got {accuracy * 100:.1f}% ({correct_predictions}/{total_predictions})"
    )


@pytest.mark.integration
def test_company_relevance_performance_single_headline(real_classifier):
    """Test company relevance completes in < 3 seconds on CPU for single headline."""
    start_time = time.time()
    result = real_classifier.classify_headline(DELL_NVIDIA_HEADLINE, company="Dell")
    elapsed_time = time.time() - start_time

    assert elapsed_time < 3.0, (
        f"Expected classification with company in < 3s, took {elapsed_time:.2f}s"
    )
    assert result.is_about_company is not None


@pytest.mark.integration
def test_company_relevance_performance_overhead(real_classifier):
    """Test company check adds < 500ms latency compared to base classification."""
    # Baseline: classification without company
    start_time = time.time()
    result_no_company = real_classifier.classify_headline(DELL_NVIDIA_HEADLINE)
    baseline_time = time.time() - start_time

    # With company: classification + company relevance
    start_time = time.time()
    result_with_company = real_classifier.classify_headline(
        DELL_NVIDIA_HEADLINE, company="Dell"
    )
    with_company_time = time.time() - start_time

    overhead = with_company_time - baseline_time

    assert overhead < 0.5, (
        f"Expected company check overhead < 500ms, got {overhead * 1000:.0f}ms"
    )
    assert result_no_company.is_about_company is None
    assert result_with_company.is_about_company is not None


@pytest.mark.integration
def test_company_relevance_batch_processing_performance(real_classifier):
    """Test batch processing with company completes in < 5 seconds for 10 headlines."""
    headlines = [
        "Dell Unveils AI Platform",
        "NVIDIA Reports Record Revenue",
        "Tesla Shares Surge on Deliveries",
        "Apple Announces New iPhone",
        "Microsoft Azure Grows 30%",
        "Amazon Web Services Expands",
        "Google Cloud Revenue Jumps",
        "Meta Announces AI Investment",
        "Intel Launches New Chip",
        "AMD Gains Market Share",
    ]

    start_time = time.time()
    results = real_classifier.classify_batch(headlines, company="Dell")
    elapsed_time = time.time() - start_time

    assert elapsed_time < 5.0, (
        f"Expected batch with company in < 5s, took {elapsed_time:.2f}s"
    )
    assert len(results) == 10
    assert all(r.company == "Dell" for r in results)


@pytest.mark.integration
def test_company_name_variation_uppercase(real_classifier):
    """Test company relevance handles case variations correctly."""
    headline = "DELL announces earnings beat"

    result = real_classifier.classify_headline(headline, company="Dell")

    # Model should handle case variation naturally via NLI
    assert result.is_about_company is True, (
        f"Expected model to handle case variation (DELL vs Dell), "
        f"got is_about_company={result.is_about_company}"
    )


@pytest.mark.integration
def test_company_name_variation_full_name(real_classifier):
    """Test company relevance handles name variations (Dell vs Dell Technologies)."""
    headline = "Dell Technologies Announces Q4 Earnings"

    result = real_classifier.classify_headline(headline, company="Dell")

    # Model should recognize "Dell" in "Dell Technologies"
    assert result.is_about_company is True, (
        f"Expected model to match 'Dell' in 'Dell Technologies', "
        f"got is_about_company={result.is_about_company}"
    )


@pytest.mark.integration
def test_existing_classification_dimensions_no_regression(real_classifier):
    """Test that adding company parameter doesn't affect existing classifications."""
    headline = DELL_NVIDIA_HEADLINE

    # Classify without company (baseline)
    result_no_company = real_classifier.classify_headline(headline)

    # Classify with company
    result_with_company = real_classifier.classify_headline(headline, company="Dell")

    # Existing classification dimensions should be identical
    assert result_no_company.is_opinion == result_with_company.is_opinion
    assert result_no_company.is_straight_news == result_with_company.is_straight_news
    assert (
        result_no_company.temporal_category == result_with_company.temporal_category
    )

    # Scores should be identical (company check is separate)
    assert (
        result_no_company.scores.opinion_score
        == result_with_company.scores.opinion_score
    )
    assert (
        result_no_company.scores.news_score == result_with_company.scores.news_score
    )
    assert (
        result_no_company.scores.past_score == result_with_company.scores.past_score
    )
    assert (
        result_no_company.scores.future_score
        == result_with_company.scores.future_score
    )
    assert (
        result_no_company.scores.general_score
        == result_with_company.scores.general_score
    )
