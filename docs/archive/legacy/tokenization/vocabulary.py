"""
Token Vocabulary Definitions
Central repository for all token definitions and mappings.
"""

from enum import Enum


class GEXToken(Enum):
    """GEX state tokens based on percentile ranges."""

    EXTREME_NEG = "GEX_EXTREME_NEG"  # < 10th percentile
    MOD_NEG = "GEX_MOD_NEG"  # 10-40th percentile
    NEUTRAL = "GEX_NEUTRAL"  # 40-60th percentile
    MOD_POS = "GEX_MOD_POS"  # 60-90th percentile
    EXTREME_POS = "GEX_EXTREME_POS"  # > 90th percentile

    @classmethod
    def from_percentile(cls, percentile) -> "GEXToken":
        """Get token from percentile value."""
        if percentile < 10:
            return cls.EXTREME_NEG
        elif percentile < 40:
            return cls.MOD_NEG
        elif percentile < 60:
            return cls.NEUTRAL
        elif percentile < 90:
            return cls.MOD_POS
        else:
            return cls.EXTREME_POS


class PriceToken(Enum):
    """Price movement tokens based on percentage changes."""

    CRASH = "PRICE_CRASH"  # < -3%
    BIG_DOWN = "PRICE_BIG_DOWN"  # -3% to -1%
    SMALL_DOWN = "PRICE_SMALL_DOWN"  # -1% to -0.25%
    FLAT = "PRICE_FLAT"  # -0.25% to 0.25%
    SMALL_UP = "PRICE_SMALL_UP"  # 0.25% to 1%
    BIG_UP = "PRICE_BIG_UP"  # 1% to 3%
    MOON = "PRICE_MOON"  # > 3%

    @classmethod
    def from_return(cls, return_pct) -> "PriceToken":
        """Get token from percentage return."""
        if return_pct < -3:
            return cls.CRASH
        elif return_pct < -1:
            return cls.BIG_DOWN
        elif return_pct < -0.25:
            return cls.SMALL_DOWN
        elif return_pct < 0.25:
            return cls.FLAT
        elif return_pct < 1:
            return cls.SMALL_UP
        elif return_pct < 3:
            return cls.BIG_UP
        else:
            return cls.MOON


class EventToken(Enum):
    """Market event tokens for special conditions."""

    CROSS_FLIP = "EVENT_CROSS_FLIP"  # GEX crosses zero
    BREAK_CALL_WALL = "EVENT_BREAK_CALL_WALL"  # Price breaks above call wall
    BREAK_PUT_SUPPORT = "EVENT_BREAK_PUT_SUPPORT"  # Price breaks below put support
    VOL_SPIKE = "EVENT_VOL_SPIKE"  # VIX > 20% daily move
    OPEX_WEEK = "EVENT_OPEX_WEEK"  # Options expiration week
    FOMC_WEEK = "EVENT_FOMC_WEEK"  # Fed meeting week
    GAMMA_SQUEEZE = "EVENT_GAMMA_SQUEEZE"  # High gamma concentration
    PIN_RISK = "EVENT_PIN_RISK"  # Price pinned at strike


class ContextToken(Enum):
    """Context tokens for temporal and structural information."""

    DAYS_TO_OPEX = "CTX_DAYS_TO_OPEX"  # Days until options expiry
    DAYS_SINCE_FOMC = "CTX_DAYS_SINCE_FOMC"  # Days since last Fed meeting
    MONTH_END = "CTX_MONTH_END"  # Month-end rebalancing
    QUARTER_END = "CTX_QUARTER_END"  # Quarter-end rebalancing
    WINDOW_DRESSING = "CTX_WINDOW_DRESSING"  # Window dressing period
    TAX_LOSS_HARVEST = "CTX_TAX_LOSS_HARVEST"  # Tax loss harvesting season


class SpecialToken(Enum):
    """Special tokens for sequence structure."""

    START = "[START]"  # Sequence start
    END = "[END]"  # Sequence end
    SEP = "[SEP]"  # Separator between segments
    ARROW = "->"  # Causal arrow
    PAD = "[PAD]"  # Padding token
    UNK = "[UNK]"  # Unknown/missing data
    MASK = "[MASK]"  # Masked token for prediction


class TokenVocabulary:
    """
    Complete token vocabulary manager for the tokenization system.
    """

    def __init__(self):
        """Initialize the vocabulary."""
        self._build_vocabulary()
        self._build_token_to_id()

    def _build_vocabulary(self):
        """Build complete vocabulary list."""
        self.vocabulary = []

        # Add all token types
        for token_enum in [GEXToken, PriceToken, EventToken, ContextToken, SpecialToken]:
            for token in token_enum:
                self.vocabulary.append(token.value)

        # Add numeric context tokens (for days)
        for days in range(0, 31):  # 0-30 days
            self.vocabulary.append(f"DAYS_{days}")

        # Add percentile tokens for fine-grained GEX
        for pct in range(0, 101, 5):  # 0, 5, 10, ..., 100
            self.vocabulary.append(f"PCT_{pct}")

    def _build_token_to_id(self):
        """Build token to ID mappings."""
        self.token_to_id = {token: idx for idx, token in enumerate(self.vocabulary)}
        self.id_to_token = {idx: token for token, idx in self.token_to_id.items()}

    def get_token_id(self, token) -> int:
        """Get numeric ID for a token."""
        return self.token_to_id.get(token, self.token_to_id[SpecialToken.UNK.value])

    def get_token_from_id(self, token_id) -> str:
        """Get token string from numeric ID."""
        return self.id_to_token.get(token_id, SpecialToken.UNK.value)

    def encode_sequence(self, tokens):
        """Encode a sequence of tokens to IDs."""
        return [self.get_token_id(token) for token in tokens]

    def decode_sequence(self, token_ids):
        """Decode a sequence of IDs to tokens."""
        return [self.get_token_from_id(tid) for tid in token_ids]

    @property
    def vocab_size(self) -> int:
        """Get vocabulary size."""
        return len(self.vocabulary)

    def get_token_ranges(self):
        """Get value ranges for each token type."""
        return {
            "GEX_PERCENTILES": {
                GEXToken.EXTREME_NEG.value: (0, 10),
                GEXToken.MOD_NEG.value: (10, 40),
                GEXToken.NEUTRAL.value: (40, 60),
                GEXToken.MOD_POS.value: (60, 90),
                GEXToken.EXTREME_POS.value: (90, 100),
            },
            "PRICE_RETURNS": {
                PriceToken.CRASH.value: (float("-inf"), -3),
                PriceToken.BIG_DOWN.value: (-3, -1),
                PriceToken.SMALL_DOWN.value: (-1, -0.25),
                PriceToken.FLAT.value: (-0.25, 0.25),
                PriceToken.SMALL_UP.value: (0.25, 1),
                PriceToken.BIG_UP.value: (1, 3),
                PriceToken.MOON.value: (3, float("inf")),
            },
        }

    def describe_token(self, token) -> str:
        """Get human-readable description of a token."""
        descriptions = {
            # GEX Tokens
            GEXToken.EXTREME_NEG.value: "Extremely negative gamma exposure (< 10th percentile)",
            GEXToken.MOD_NEG.value: "Moderately negative gamma exposure (10-40th percentile)",
            GEXToken.NEUTRAL.value: "Neutral gamma exposure (40-60th percentile)",
            GEXToken.MOD_POS.value: "Moderately positive gamma exposure (60-90th percentile)",
            GEXToken.EXTREME_POS.value: "Extremely positive gamma exposure (> 90th percentile)",
            # Price Tokens
            PriceToken.CRASH.value: "Market crash (< -3% daily return)",
            PriceToken.BIG_DOWN.value: "Large decline (-3% to -1% daily return)",
            PriceToken.SMALL_DOWN.value: "Small decline (-1% to -0.25% daily return)",
            PriceToken.FLAT.value: "Flat movement (-0.25% to 0.25% daily return)",
            PriceToken.SMALL_UP.value: "Small rally (0.25% to 1% daily return)",
            PriceToken.BIG_UP.value: "Large rally (1% to 3% daily return)",
            PriceToken.MOON.value: "Extreme rally (> 3% daily return)",
            # Event Tokens
            EventToken.CROSS_FLIP.value: "GEX crosses zero (dealer positioning flip)",
            EventToken.BREAK_CALL_WALL.value: "Price breaks above major call wall",
            EventToken.BREAK_PUT_SUPPORT.value: "Price breaks below major put support",
            EventToken.VOL_SPIKE.value: "Volatility spike (VIX > 20% daily move)",
            EventToken.OPEX_WEEK.value: "Options expiration week",
            EventToken.FOMC_WEEK.value: "Federal Reserve meeting week",
            EventToken.GAMMA_SQUEEZE.value: "High gamma concentration causing squeeze",
            EventToken.PIN_RISK.value: "Price pinned at major strike level",
            # Context Tokens
            ContextToken.MONTH_END.value: "Month-end rebalancing period",
            ContextToken.QUARTER_END.value: "Quarter-end rebalancing period",
            ContextToken.WINDOW_DRESSING.value: "Portfolio window dressing period",
            ContextToken.TAX_LOSS_HARVEST.value: "Tax loss harvesting season",
        }

        return descriptions.get(token, f"Token: {token}")
