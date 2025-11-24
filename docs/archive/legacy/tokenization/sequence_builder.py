"""
Sequence Builder
Combines tokens from different sources to create LLM-ready sequences.
"""

import datetime
import json
import logging

import numpy as np
import pandas as pd

from src.utils.config_manager import get_config

from .event_tokenizer import EventTokenizer
from .gex_tokenizer import GEXTokenizer
from .price_tokenizer import PriceTokenizer
from .vocabulary import SpecialToken, TokenVocabulary

logger = logging.getLogger(__name__)


class SequenceBuilder:
    """
    Build token sequences for LLM analysis from market data.
    """

    def __init__(self, max_sequence_length=None, context_window_days=None):
        """
        Initialize sequence builder.

        Args:
            max_sequence_length: Maximum tokens per sequence (default from config)
            context_window_days: Default lookback period for sequences (default from config)
        """
        config = get_config()

        # Use config values as defaults, allow override via parameters
        self.max_sequence_length = max_sequence_length or config.get(
            "tokenization.sequence_builder.max_sequence_length", 512
        )
        self.context_window_days = context_window_days or config.get(
            "tokenization.sequence_builder.context_window_days", 20
        )
        self.pattern_length = config.get("tokenization.sequence_builder.pattern_length", 5)
        self.target_horizon = config.get("tokenization.sequence_builder.target_horizon", 1)
        self.stride = config.get("tokenization.sequence_builder.stride", 1)
        self.timeframes = config.get("tokenization.sequence_builder.timeframes", [5, 10, 20])
        self.model_token_limits = config.get(
            "tokenization.sequence_builder.model_token_limits",
            {"gpt-4o-mini": 4096, "gpt-4o": 8192, "gpt-3.5-turbo": 4096},
        )

        # Initialize tokenizers
        self.gex_tokenizer = GEXTokenizer()
        self.price_tokenizer = PriceTokenizer()
        self.event_tokenizer = EventTokenizer()
        self.vocabulary = TokenVocabulary()

    def build_sequence(self, data, target_date: datetime.datetime, lookback_days=None, include_target=True):
        """
        Build a complete sequence for a target date.

        Args:
            data: DataFrame with market data (must have 'gex', 'price' columns)
            target_date: Date to build sequence for
            lookback_days: Days to look back (default uses context_window_days)
            include_target: Whether to include target date in sequence

        Returns:
            Dictionary with tokens and metadata
        """
        if lookback_days is None:
            lookback_days = self.context_window_days

        # Get data window
        start_date = target_date - datetime.timedelta(days=lookback_days)
        if include_target:
            end_date = target_date
        else:
            end_date = target_date - datetime.timedelta(days=1)

        window_data = data[start_date:end_date]

        if len(window_data) == 0:
            logger.warning(f"No data available for {target_date} with {lookback_days} day lookback")
            return self._empty_sequence()

        # Build token components
        tokens = {"gex": [], "price": [], "events": [], "context": []}

        # Tokenize GEX if available
        if "gex" in window_data.columns:
            gex_tokens = self.gex_tokenizer.tokenize_series(window_data["gex"], rolling_window=True)
            tokens["gex"] = gex_tokens

        # Tokenize prices if available
        if "price" in window_data.columns:
            price_tokens = self.price_tokenizer.tokenize_price_series(window_data["price"])
            tokens["price"] = price_tokens

        # Detect and tokenize events
        tokens["events"] = [""] * len(window_data)  # Initialize events list
        if "gex" in window_data.columns:
            gex_events = self.event_tokenizer.detect_gex_events(window_data["gex"])
            for event in gex_events:
                if event["date"] in window_data.index:
                    idx = window_data.index.get_loc(event["date"])
                    tokens["events"][idx] = event["event"]

        # Add context tokens for target date
        context = self.event_tokenizer.generate_context_tokens(target_date)
        tokens["context"] = context

        # Combine into final sequence
        sequence = self._combine_tokens(tokens, window_data.index)

        # Add metadata
        metadata = {
            "target_date": target_date.isoformat(),
            "lookback_days": lookback_days,
            "actual_days": len(window_data),
            "token_counts": {k: len(v) for k, v in tokens.items()},
            "sequence_length": len(sequence),
        }

        return {"sequence": sequence, "tokens": tokens, "metadata": metadata}

    def build_pattern_sequences(self, data, pattern_length=None, target_horizon=None, stride=None):
        """
        Build sequences for pattern mining.

        Args:
            data: Market data DataFrame
            pattern_length: Length of input pattern (default from config)
            target_horizon: Days ahead to predict (default from config)
            stride: Step size between sequences (default from config)

        Returns:
            List of pattern sequences with targets
        """
        # Use instance config values as defaults
        pattern_length = pattern_length or self.pattern_length
        target_horizon = target_horizon or self.target_horizon
        stride = stride or self.stride

        sequences = []

        # Ensure we have enough data
        min_length = pattern_length + target_horizon
        if len(data) < min_length:
            logger.warning(f"Insufficient data: {len(data)} < {min_length}")
            return sequences

        # Generate sequences with sliding window
        for i in range(0, len(data) - min_length + 1, stride):
            # Input window
            input_start = i
            input_end = i + pattern_length
            input_data = data.iloc[input_start:input_end]

            # Target window
            target_start = input_end
            target_end = target_start + target_horizon
            target_data = data.iloc[target_start:target_end]

            # Build input sequence
            input_tokens = self._build_pattern_tokens(input_data)

            # Build target tokens
            target_tokens = self._build_pattern_tokens(target_data)

            # Create pattern sequence
            pattern_seq = {
                "input": input_tokens,
                "target": target_tokens,
                "pattern": input_tokens + [SpecialToken.ARROW.value] + target_tokens,
                "metadata": {
                    "input_dates": input_data.index.tolist(),
                    "target_dates": target_data.index.tolist(),
                    "pattern_id": f"pattern_{i}",
                },
            }

            sequences.append(pattern_seq)

        return sequences

    def build_multi_timeframe_sequence(self, data, target_date: datetime.datetime, timeframes=None):
        """
        Build sequences with multiple timeframes.

        Args:
            data: Market data
            target_date: Target date
            timeframes: List of lookback periods (default from config)

        Returns:
            Multi-timeframe sequence dictionary
        """
        # Use instance config values as defaults
        timeframes = timeframes or self.timeframes
        multi_sequence = {
            "timeframes": {},
            "combined": [],
            "metadata": {"target_date": target_date.isoformat(), "timeframes": timeframes},
        }

        # Build sequence for each timeframe
        for tf in timeframes:
            seq = self.build_sequence(data, target_date, lookback_days=tf)
            multi_sequence["timeframes"][f"tf_{tf}"] = seq

            # Add timeframe marker
            tf_tokens = [f"[TF_{tf}]"] + seq["sequence"] + [f"[/TF_{tf}]"]
            multi_sequence["combined"].extend(tf_tokens)

        # Truncate if too long
        if len(multi_sequence["combined"]) > self.max_sequence_length:
            multi_sequence["combined"] = multi_sequence["combined"][: self.max_sequence_length]
            multi_sequence["metadata"]["truncated"] = True

        return multi_sequence

    def _combine_tokens(self, tokens, dates: pd.DatetimeIndex):
        """
        Combine different token types into a single sequence.

        Args:
            tokens: Dictionary of token lists by type
            dates: Date index for alignment

        Returns:
            Combined token sequence
        """
        sequence = [SpecialToken.START.value]

        # Combine daily tokens
        for i, date in enumerate(dates):
            daily_tokens = []

            # Add date marker
            daily_tokens.append(f"[DAY_{i}]")

            # Add GEX token
            if "gex" in tokens and i < len(tokens["gex"]):
                daily_tokens.append(tokens["gex"][i])

            # Add price token
            if "price" in tokens and i < len(tokens["price"]):
                daily_tokens.append(tokens["price"][i])

            # Add event tokens
            if "events" in tokens and i < len(tokens["events"]) and tokens["events"][i]:
                daily_tokens.append(tokens["events"][i])

            sequence.extend(daily_tokens)

        # Add context tokens at the end
        if "context" in tokens and tokens["context"]:
            sequence.append(SpecialToken.SEP.value)
            sequence.extend(tokens["context"])

        sequence.append(SpecialToken.END.value)

        return sequence

    def _build_pattern_tokens(self, data):
        """Build tokens for pattern mining."""
        tokens = []

        # Simple tokenization for pattern mining
        if "gex" in data.columns:
            gex_tokens = self.gex_tokenizer.tokenize_series(data["gex"], rolling_window=False)
            tokens.extend(gex_tokens)

        if "price" in data.columns:
            price_tokens = self.price_tokenizer.tokenize_price_series(data["price"])
            tokens.extend(price_tokens)

        return tokens

    def _empty_sequence(self):
        """Return empty sequence structure."""
        return {
            "sequence": [SpecialToken.START.value, SpecialToken.UNK.value, SpecialToken.END.value],
            "tokens": {},
            "metadata": {"error": "No data available"},
        }

    def encode_for_llm(self, sequence, model="gpt-4o-mini"):
        """
        Encode sequence for specific LLM model.

        Args:
            sequence: Token sequence
            model: Target model name

        Returns:
            Encoded sequence with model-specific formatting
        """
        # Use model-specific token limits from config
        max_tokens = self.model_token_limits.get(model, 4096)

        # Truncate if needed
        if len(sequence) > max_tokens:
            sequence = sequence[: max_tokens - 1] + [SpecialToken.END.value]

        # Convert to string representation
        text_sequence = " ".join(sequence)

        return {
            "text": text_sequence,
            "tokens": sequence,
            "token_count": len(sequence),
            "model": model,
            "truncated": len(sequence) >= max_tokens,
        }

    def validate_sequences(self, sequences):
        """
        Validate generated sequences.

        Args:
            sequences: List of sequences to validate

        Returns:
            Validation report
        """
        validation = {"total_sequences": len(sequences), "valid_sequences": 0, "issues": [], "statistics": {}}

        lengths = []
        token_types = set()

        for i, seq in enumerate(sequences):
            # Check structure
            if "sequence" not in seq:
                validation["issues"].append(f"Sequence {i}: Missing 'sequence' key")
                continue

            sequence = seq["sequence"]
            lengths.append(len(sequence))

            # Check for required tokens
            if SpecialToken.START.value not in sequence:
                validation["issues"].append(f"Sequence {i}: Missing START token")
            if SpecialToken.END.value not in sequence:
                validation["issues"].append(f"Sequence {i}: Missing END token")

            # Collect token types
            for token in sequence:
                token_types.add(token.split("_")[0] if "_" in token else token)

            # Check length
            if len(sequence) > self.max_sequence_length:
                validation["issues"].append(f"Sequence {i}: Too long ({len(sequence)} > {self.max_sequence_length})")
            else:
                validation["valid_sequences"] += 1

        # Calculate statistics
        if lengths:
            validation["statistics"] = {
                "mean_length": np.mean(lengths),
                "std_length": np.std(lengths),
                "min_length": min(lengths),
                "max_length": max(lengths),
                "unique_token_types": len(token_types),
                "token_types": list(token_types),
            }

        validation["validity_rate"] = validation["valid_sequences"] / len(sequences) if sequences else 0

        return validation

    def save_sequences(self, sequences, filepath, format="jsonl"):
        """
        Save sequences to file.

        Args:
            sequences: Sequences to save
            filepath: Output file path
            format: Output format ('json', 'jsonl', 'csv')
        """
        if format == "jsonl":
            with open(filepath, "w") as f:
                for seq in sequences:
                    f.write(json.dumps(seq) + "\n")
        elif format == "json":
            with open(filepath, "w") as f:
                json.dump(sequences, f, indent=2, default=str)
        elif format == "csv":
            # Convert to DataFrame for CSV
            df_data = []
            for seq in sequences:
                df_data.append(
                    {
                        "sequence": " ".join(seq.get("sequence", [])),
                        "metadata": json.dumps(seq.get("metadata", {}), default=str),
                    }
                )
            pd.DataFrame(df_data).to_csv(filepath, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Saved {len(sequences)} sequences to {filepath}")
