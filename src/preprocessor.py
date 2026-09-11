"""
Text preprocessing and PII sanitization for incoming customer tweets.
Ensures tweets are normalized, cleaned, and safe for processing.
"""

import re
from typing import List, Tuple
from src.models import PreprocessedTweet


class TweetPreprocessor:
    # Regex patterns
    HANDLE_PATTERN = re.compile(r"@[\w_]+", re.IGNORECASE)
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
    PHONE_PATTERN = re.compile(r"(?<![#\w])(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?![-\d])")
    CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
    URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
    MULTIPLE_SPACES = re.compile(r"\s+")

    def clean(self, raw_tweet: str) -> PreprocessedTweet:
        """
        Cleans and sanitizes an inbound tweet:
        - Extracts handles
        - Masks any accidentally shared PII (credit cards, emails, phone numbers)
        - Normalizes whitespace
        """
        raw_text = raw_tweet.strip()
        handles = self.HANDLE_PATTERN.findall(raw_text)

        masked_text = raw_text
        contains_pii = False

        # Mask Card Numbers
        if self.CARD_PATTERN.search(masked_text):
            masked_text = self.CARD_PATTERN.sub("[MASKED_CARD_NUMBER]", masked_text)
            contains_pii = True

        # Mask Emails
        if self.EMAIL_PATTERN.search(masked_text):
            masked_text = self.EMAIL_PATTERN.sub("[MASKED_EMAIL]", masked_text)
            contains_pii = True

        # Mask Phone Numbers
        if self.PHONE_PATTERN.search(masked_text):
            masked_text = self.PHONE_PATTERN.sub("[MASKED_PHONE]", masked_text)
            contains_pii = True

        # Normalize spaces
        cleaned = self.MULTIPLE_SPACES.sub(" ", masked_text).strip()

        return PreprocessedTweet(
            raw_text=raw_text,
            cleaned_text=cleaned,
            handles_detected=handles,
            contains_masked_pii=contains_pii,
            original_length=len(raw_text),
            cleaned_length=len(cleaned)
        )
