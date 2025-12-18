"""Checkpoint Manager for Continuous GEX Backtesting Handles state persistence and resumption for long-running
experiments."""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BacktestCheckpoint:
    """Checkpoint data structure for experiment state."""

    experiment_id: str
    strategy_version: str
    symbol: str
    start_date: str
    end_date: str
    last_completed_date: str
    checkpoint_date: str
    trading_days_completed: int
    total_trading_days: int
    signals_generated: int
    current_performance: Dict
    experiment_config: Dict
    batch_data_prepared: bool = False
    batch_preparation_complete: bool = False


class CheckpointManager:
    """Manages checkpoints for resumable continuous backtesting.

    Features:
    - Save state every N trading days
    - Resume from any checkpoint
    - Track experiment progress
    - Handle batch preparation state
    - Prevent duplicate work
    """

    def __init__(self, checkpoint_dir: str = "reports/checkpoints"):
        """Initialize checkpoint manager with storage directory."""
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Checkpoint configuration
        self.checkpoint_frequency = 5  # Save every 5 trading days
        self.max_checkpoints_per_experiment = 10  # Keep latest 10 checkpoints

        logger.info(f"Initialized CheckpointManager at {self.checkpoint_dir}")

    def save_checkpoint(self, checkpoint: BacktestCheckpoint) -> str:
        """Save experiment checkpoint to disk.

        Args:
            checkpoint: BacktestCheckpoint object with current state

        Returns:
            Path to saved checkpoint file
        """
        # Generate checkpoint filename
        checkpoint_filename = (
            f"{checkpoint.experiment_id}_{checkpoint.strategy_version}_"
            f"{checkpoint.last_completed_date.replace('-', '')}.json"
        )
        checkpoint_path = self.checkpoint_dir / checkpoint_filename

        # Update checkpoint timestamp
        checkpoint.checkpoint_date = datetime.now().isoformat()

        try:
            # Save checkpoint as JSON
            with open(checkpoint_path, "w") as f:
                json.dump(asdict(checkpoint), f, indent=2, default=str)

            logger.info(f"Saved checkpoint: {checkpoint_filename}")
            logger.info(f"  Progress: {checkpoint.trading_days_completed}/{checkpoint.total_trading_days} trading days")
            logger.info(f"  Signals: {checkpoint.signals_generated}")

            # Clean up old checkpoints
            self._cleanup_old_checkpoints(checkpoint.experiment_id, checkpoint.strategy_version)

            return str(checkpoint_path)

        except Exception as e:
            logger.error(f"Failed to save checkpoint {checkpoint_filename}: {e}")
            raise

    def load_checkpoint(self, experiment_id: str, strategy_version: str) -> Optional[BacktestCheckpoint]:
        """Load the latest checkpoint for an experiment.

        Args:
            experiment_id: Unique experiment identifier
            strategy_version: Strategy version (V0, V1, etc.)

        Returns:
            BacktestCheckpoint if found, None otherwise
        """
        # Find all checkpoints for this experiment
        pattern = f"{experiment_id}_{strategy_version}_*.json"
        checkpoint_files = list(self.checkpoint_dir.glob(pattern))

        if not checkpoint_files:
            logger.info(f"No checkpoints found for {experiment_id}_{strategy_version}")
            return None

        # Get the latest checkpoint (by filename date)
        latest_checkpoint = max(checkpoint_files, key=lambda p: p.stem.split("_")[-1])

        try:
            with open(latest_checkpoint, "r") as f:
                checkpoint_data = json.load(f)

            checkpoint = BacktestCheckpoint(**checkpoint_data)

            logger.info(f"Loaded checkpoint: {latest_checkpoint.name}")
            logger.info(f"  Last completed: {checkpoint.last_completed_date}")
            logger.info(f"  Progress: {checkpoint.trading_days_completed}/{checkpoint.total_trading_days}")

            return checkpoint

        except Exception as e:
            logger.error(f"Failed to load checkpoint {latest_checkpoint}: {e}")
            return None

    def should_checkpoint(self, days_since_last: int) -> bool:
        """Determine if a checkpoint should be saved.

        Args:
            days_since_last: Trading days since last checkpoint

        Returns:
            True if checkpoint should be saved
        """
        return days_since_last >= self.checkpoint_frequency

    def get_experiment_status(self, experiment_id: str = None) -> List[Dict]:
        """Get status of all experiments or specific experiment.

        Args:
            experiment_id: Optional specific experiment ID

        Returns:
            List of experiment status dictionaries
        """
        if experiment_id:
            pattern = f"{experiment_id}_*.json"
        else:
            pattern = "*.json"

        checkpoint_files = list(self.checkpoint_dir.glob(pattern))

        if not checkpoint_files:
            return []

        # Group by experiment_id and strategy_version
        experiments = {}
        for checkpoint_file in checkpoint_files:
            try:
                with open(checkpoint_file, "r") as f:
                    checkpoint_data = json.load(f)

                exp_id = checkpoint_data["experiment_id"]
                strategy = checkpoint_data["strategy_version"]
                key = f"{exp_id}_{strategy}"

                if key not in experiments:
                    experiments[key] = checkpoint_data
                else:
                    # Keep the latest checkpoint
                    current_date = experiments[key]["last_completed_date"]
                    new_date = checkpoint_data["last_completed_date"]
                    if new_date > current_date:
                        experiments[key] = checkpoint_data

            except Exception as e:
                logger.warning(f"Failed to read checkpoint {checkpoint_file}: {e}")
                continue

        # Format status information
        status_list = []
        for exp_data in experiments.values():
            progress_pct = (exp_data["trading_days_completed"] / exp_data["total_trading_days"]) * 100
            status = "Complete" if progress_pct >= 100 else "In Progress"

            status_list.append(
                {
                    "experiment_id": exp_data["experiment_id"],
                    "strategy_version": exp_data["strategy_version"],
                    "symbol": exp_data["symbol"],
                    "date_range": f"{exp_data['start_date']} to {exp_data['end_date']}",
                    "last_completed": exp_data["last_completed_date"],
                    "progress_pct": round(progress_pct, 1),
                    "status": status,
                    "signals_generated": exp_data["signals_generated"],
                    "checkpoint_date": exp_data["checkpoint_date"],
                }
            )

        return sorted(status_list, key=lambda x: x["checkpoint_date"], reverse=True)

    def resume_from_checkpoint(self, experiment_id: str, strategy_version: str) -> Optional[Dict]:
        """Prepare to resume experiment from checkpoint.

        Args:
            experiment_id: Experiment identifier
            strategy_version: Strategy version

        Returns:
            Resume information dictionary or None
        """
        checkpoint = self.load_checkpoint(experiment_id, strategy_version)
        if not checkpoint:
            return None

        # Calculate resume parameters
        progress_pct = (checkpoint.trading_days_completed / checkpoint.total_trading_days) * 100

        if progress_pct >= 100:
            logger.info(f"Experiment {experiment_id}_{strategy_version} already complete")
            return {"status": "complete", "checkpoint": checkpoint, "resume_needed": False}

        # Calculate next start date
        last_date = datetime.strptime(checkpoint.last_completed_date, "%Y-%m-%d")
        next_date = last_date + timedelta(days=1)

        logger.info(f"Experiment {experiment_id}_{strategy_version} can resume from {next_date.strftime('%Y-%m-%d')}")

        return {
            "status": "resumable",
            "checkpoint": checkpoint,
            "resume_needed": True,
            "resume_from_date": next_date.strftime("%Y-%m-%d"),
            "remaining_days": checkpoint.total_trading_days - checkpoint.trading_days_completed,
            "progress_pct": progress_pct,
        }

    def _cleanup_old_checkpoints(self, experiment_id: str, strategy_version: str):
        """Remove old checkpoints, keeping only the latest N."""
        pattern = f"{experiment_id}_{strategy_version}_*.json"
        checkpoint_files = list(self.checkpoint_dir.glob(pattern))

        if len(checkpoint_files) <= self.max_checkpoints_per_experiment:
            return

        # Sort by date in filename and keep the latest
        checkpoint_files.sort(key=lambda p: p.stem.split("_")[-1], reverse=True)
        files_to_remove = checkpoint_files[self.max_checkpoints_per_experiment :]

        for old_file in files_to_remove:
            try:
                old_file.unlink()
                logger.debug(f"Removed old checkpoint: {old_file.name}")
            except Exception as e:
                logger.warning(f"Failed to remove old checkpoint {old_file}: {e}")

    def create_experiment_checkpoint(
        self, experiment_id: str, strategy_version: str, symbol: str, start_date: str, end_date: str, config: Dict
    ) -> BacktestCheckpoint:
        """Create initial checkpoint for new experiment.

        Args:
            experiment_id: Unique experiment identifier
            strategy_version: Strategy version
            symbol: Trading symbol
            start_date: Experiment start date
            end_date: Experiment end date
            config: Experiment configuration

        Returns:
            New BacktestCheckpoint
        """
        # Calculate total trading days (rough estimate)
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        total_days = (end - start).days

        # Rough estimate: 5 trading days per week
        estimated_trading_days = int(total_days * (5 / 7))

        checkpoint = BacktestCheckpoint(
            experiment_id=experiment_id,
            strategy_version=strategy_version,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            last_completed_date=start_date,
            checkpoint_date=datetime.now().isoformat(),
            trading_days_completed=0,
            total_trading_days=estimated_trading_days,
            signals_generated=0,
            current_performance={},
            experiment_config=config,
            batch_data_prepared=False,
            batch_preparation_complete=False,
        )

        return checkpoint

    def mark_batch_preparation_complete(self, checkpoint: BacktestCheckpoint) -> BacktestCheckpoint:
        """Mark that batch data preparation is complete."""
        checkpoint.batch_data_prepared = True
        checkpoint.batch_preparation_complete = True

        # Save special batch preparation checkpoint
        batch_checkpoint_filename = (
            f"{checkpoint.experiment_id}_{checkpoint.strategy_version}_" f"batch_prep_complete.json"
        )
        batch_checkpoint_path = self.checkpoint_dir / batch_checkpoint_filename

        try:
            with open(batch_checkpoint_path, "w") as f:
                json.dump(asdict(checkpoint), f, indent=2, default=str)

            logger.info(f"Saved batch preparation checkpoint: {batch_checkpoint_filename}")

        except Exception as e:
            logger.error(f"Failed to save batch preparation checkpoint: {e}")

        return checkpoint
