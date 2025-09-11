"""
Reports Manager for GEX-LLM Analysis Outputs

Handles saving and organizing all analysis results, calculations, and reports.
Keeps outputs separate from cache to maintain clean data pipeline.
"""

import json
from pathlib import Path
import pandas as pd
import logging
from typing import Dict, Any, List
from .date_utils import now_timestamp, now_iso

logger = logging.getLogger(__name__)


class ReportsManager:
    """
    Manages all analysis outputs and reports.
    
    Provides organized storage for:
    - GEX calculation results
    - Pattern analysis outputs  
    - Agent conversation logs
    - Data quality reports
    """

    def __init__(self, base_dir: str = "reports"):
        """Initialize reports manager with directory structure."""
        self.base_dir = Path(base_dir)
        
        # Create subdirectories
        self.gex_dir = self.base_dir / "gex_calculations"
        self.pattern_dir = self.base_dir / "pattern_analysis"
        self.quality_dir = self.base_dir / "data_quality"
        self.agent_dir = self.base_dir / "agent_outputs"
        self.demo_dir = self.base_dir / "demo_results"
        
        # Ensure all directories exist
        for directory in [self.gex_dir, self.pattern_dir, self.quality_dir, 
                         self.agent_dir, self.demo_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    # ===========================
    # GEX Results Storage
    # ===========================
    
    def save_gex_results(self, symbol, results: Dict[Any, Any], 
                        trading_date= None, 
                        is_demo: bool = False) -> Path:
        """
        Save GEX calculation results.
        
        Args:
            symbol: Stock symbol
            results: GEX calculation results dictionary
            trading_date: Optional trading date
            is_demo: Save to demo folder if True
            
        Returns:
            Path to saved file
        """
        timestamp = now_timestamp()
        
        if trading_date:
            filename = f"{symbol}_{trading_date}_{timestamp}_gex_results.json"
        else:
            filename = f"{symbol}_{timestamp}_gex_results.json"
        
        save_dir = self.demo_dir if is_demo else self.gex_dir
        file_path = save_dir / filename
        
        # Add metadata
        output_data = {
            'metadata': {
                'symbol': symbol,
                'trading_date': trading_date,
                'generated_at': now_iso(),
                'type': 'gex_calculation_results'
            },
            'results': results
        }
        
        with open(file_path, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        logger.info(f"Saved GEX results to {file_path}")
        return file_path
    
    def save_gex_time_series(self, symbol, data: pd.DataFrame, 
                           is_demo: bool = False) -> Path:
        """Save GEX time series data as CSV."""
        timestamp = now_timestamp()
        filename = f"{symbol}_{timestamp}_gex_timeseries.csv"
        
        save_dir = self.demo_dir if is_demo else self.gex_dir
        file_path = save_dir / filename
        
        data.to_csv(file_path, index=True)
        logger.info(f"Saved GEX time series to {file_path}")
        return file_path
    
    # ===========================
    # Pattern Analysis Storage
    # ===========================
    
    def save_pattern_analysis(self, pattern_type, results: Dict[Any, Any],
                            symbol= None, 
                            is_demo: bool = False) -> Path:
        """Save pattern analysis results."""
        timestamp = now_timestamp()
        
        if symbol:
            filename = f"{pattern_type}_{symbol}_{timestamp}_analysis.json"
        else:
            filename = f"{pattern_type}_{timestamp}_analysis.json"
        
        save_dir = self.demo_dir if is_demo else self.pattern_dir
        file_path = save_dir / filename
        
        output_data = {
            'metadata': {
                'pattern_type': pattern_type,
                'symbol': symbol,
                'generated_at': now_iso(),
                'type': 'pattern_analysis_results'
            },
            'analysis': results
        }
        
        with open(file_path, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        logger.info(f"Saved pattern analysis to {file_path}")
        return file_path
    
    # ===========================
    # Agent Outputs Storage
    # ===========================
    
    def save_agent_conversation(self, agent_names: List[str], 
                              conversation_log: List[Dict[Any, Any]], 
                              is_demo: bool = False) -> Path:
        """Save multi-agent conversation log."""
        timestamp = now_timestamp()
        agents_str = "_".join(agent_names)
        filename = f"{agents_str}_{timestamp}_conversation.json"
        
        save_dir = self.demo_dir if is_demo else self.agent_dir
        file_path = save_dir / filename
        
        output_data = {
            'metadata': {
                'agents': agent_names,
                'generated_at': now_iso(),
                'type': 'agent_conversation_log',
                'message_count': len(conversation_log)
            },
            'conversation': conversation_log
        }
        
        with open(file_path, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        logger.info(f"Saved agent conversation to {file_path}")
        return file_path
    
    def save_agent_results(self, agent_name, task, 
                          results: Dict[Any, Any], is_demo: bool = False) -> Path:
        """Save individual agent task results."""
        timestamp = now_timestamp()
        filename = f"{agent_name}_{task}_{timestamp}_results.json"
        
        save_dir = self.demo_dir if is_demo else self.agent_dir
        file_path = save_dir / filename
        
        output_data = {
            'metadata': {
                'agent_name': agent_name,
                'task': task,
                'generated_at': now_iso(),
                'type': 'agent_task_results'
            },
            'results': results
        }
        
        with open(file_path, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        logger.info(f"Saved agent results to {file_path}")
        return file_path
    
    # ===========================
    # Data Quality Reports
    # ===========================
    
    def save_quality_report(self, symbol, report: Dict[Any, Any],
                           data_type: str = "options", 
                           is_demo: bool = False) -> Path:
        """Save data quality assessment report."""
        timestamp = now_timestamp()
        filename = f"{symbol}_{data_type}_{timestamp}_quality_report.json"
        
        save_dir = self.demo_dir if is_demo else self.quality_dir
        file_path = save_dir / filename
        
        output_data = {
            'metadata': {
                'symbol': symbol,
                'data_type': data_type,
                'generated_at': now_iso(),
                'type': 'data_quality_report'
            },
            'report': report
        }
        
        with open(file_path, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        logger.info(f"Saved quality report to {file_path}")
        return file_path
    
    # ===========================
    # Utility Methods
    # ===========================
    
    def list_reports(self, category: str = "all") :
        """List available reports by category."""
        if category == "gex":
            return list(self.gex_dir.glob("*.json")) + list(self.gex_dir.glob("*.csv"))
        elif category == "patterns":
            return list(self.pattern_dir.glob("*.json"))
        elif category == "agents":
            return list(self.agent_dir.glob("*.json"))
        elif category == "quality":
            return list(self.quality_dir.glob("*.json"))
        elif category == "demo":
            return list(self.demo_dir.glob("*"))
        else:  # all
            all_files = []
            for directory in [self.gex_dir, self.pattern_dir, self.quality_dir, 
                            self.agent_dir, self.demo_dir]:
                all_files.extend(list(directory.glob("*")))
            return all_files
    
    def cleanup_demo_results(self, older_than_days: int = 7) -> int:
        """Clean up old demo results."""
        from datetime import datetime
        cutoff_time = datetime.now().timestamp() - (older_than_days * 24 * 3600)
        cleaned = 0
        
        for file_path in self.demo_dir.glob("*"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                cleaned += 1
        
        logger.info(f"Cleaned {cleaned} demo files older than {older_than_days} days")
        return cleaned
    
    def get_summary(self) :
        """Get summary of all reports."""
        summary = {}
        
        for category, directory in [
            ("gex_calculations", self.gex_dir),
            ("pattern_analysis", self.pattern_dir), 
            ("data_quality", self.quality_dir),
            ("agent_outputs", self.agent_dir),
            ("demo_results", self.demo_dir)
        ]:
            files = list(directory.glob("*"))
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            
            summary[category] = {
                "file_count": len(files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "latest": max([f.stat().st_mtime for f in files if f.is_file()], 
                            default=0)
            }
        
        return summary


# Global instance
reports_manager = ReportsManager()