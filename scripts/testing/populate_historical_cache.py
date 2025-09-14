#!/usr/bin/env python3
"""
Historical Data Population Script
Uses Alpha Vantage Premium API to populate cache with historical options data.
"""

import sys
from pathlib import Path
import logging
from datetime import datetime, timedelta

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from agents.data_retrieval_agent import DataRetrievalAgent
from gex.live_gex_interface import LiveGEXInterface

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_premium_api():
    """Test the Alpha Vantage Premium API configuration."""
    
    logger.info("Testing Alpha Vantage Premium API configuration...")
    
    # Initialize agent
    agent = DataRetrievalAgent(data_source="production", validate=True)
    gex_interface = LiveGEXInterface(validate_data=True)
    
    # Test with a recent date
    test_date = '2024-01-02'
    test_symbol = 'SPY'
    
    logger.info(f"Testing GEX calculation for {test_symbol} on {test_date}")
    
    result = gex_interface.calculate_gex_for_symbol(
        symbol=test_symbol,
        date=test_date
    )
    
    if result['status'] == 'success':
        logger.info(f"✅ Success! GEX: ${result.get('net_gex', 0):,.0f}")
        logger.info(f"Data source: {result.get('data_source')}")
        logger.info(f"Spot price: ${result.get('spot_price', 0):.2f}")
    else:
        logger.error(f"❌ Failed: {result.get('message', 'Unknown error')}")
    
    # Show stats
    stats = gex_interface.get_stats()
    logger.info(f"Interface stats: {stats}")
    
    return result['status'] == 'success'

if __name__ == "__main__":
    success = test_premium_api()
    if success:
        print("✅ Alpha Vantage Premium API is configured and working!")
    else:
        print("❌ Alpha Vantage Premium API test failed")