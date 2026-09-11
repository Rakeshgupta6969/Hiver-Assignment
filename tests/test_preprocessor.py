"""
Unit tests for text preprocessing and PII masking.
"""

import pytest
from src.preprocessor import TweetPreprocessor


@pytest.fixture
def preprocessor():
    return TweetPreprocessor()


def test_handle_extraction(preprocessor):
    tweet = "@AmazonHelp @UPS where is my order? Please assist @support"
    res = preprocessor.clean(tweet)
    assert "@AmazonHelp" in res.handles_detected
    assert "@UPS" in res.handles_detected
    assert "@support" in res.handles_detected
    assert res.contains_masked_pii is False


def test_credit_card_pii_masking(preprocessor):
    tweet = "Refund my card 4532 8821 9921 3321 right now!"
    res = preprocessor.clean(tweet)
    assert "[MASKED_CARD_NUMBER]" in res.cleaned_text
    assert "4532" not in res.cleaned_text
    assert res.contains_masked_pii is True


def test_email_pii_masking(preprocessor):
    tweet = "Send invoice to test.user@example.com for order 123"
    res = preprocessor.clean(tweet)
    assert "[MASKED_EMAIL]" in res.cleaned_text
    assert "test.user@example.com" not in res.cleaned_text
    assert res.contains_masked_pii is True


def test_phone_number_masking(preprocessor):
    tweet = "Call me at +1 (555) 234-5678 regarding the delayed package"
    res = preprocessor.clean(tweet)
    assert "[MASKED_PHONE]" in res.cleaned_text
    assert res.contains_masked_pii is True


def test_whitespace_normalization(preprocessor):
    tweet = "   Hello    @AmazonHelp   my     package   is late.   \n\n\n  "
    res = preprocessor.clean(tweet)
    assert res.cleaned_text == "Hello @AmazonHelp my package is late."
