#!/usr/bin/env python3
"""
Simple Model Testing Script
Direct test of GPT-4o, O3-mini, and O4-mini on COVID crash event
"""

import sys
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

async def test_single_model(model_name: str):
    """Test a single model on the COVID crash event."""
    print(f"\n🔬 Testing {model_name} on covid_crash_2020")

    try:
        # Import here to avoid circular imports
        from llm.autogen_market_mechanics import AutoGenMarketMechanics

        # Initialize AutoGen with specific model
        llm = AutoGenMarketMechanics(model=model_name)

        # Create test prompt similar to what validation framework uses
        test_prompt = """Analyze the market mechanics using the WHO forces WHOM to do WHAT framework.

Date: Day T+0 (anonymized date)
Gamma Exposure (GEX) Data:
- Net GEX: 211,032 (positive gamma regime)
- Flip Point: $1190.02
- Current Price: $1190.02 (exactly at flip point)
- Total Gamma: 0
- Gamma Concentration: 0% (very low)
- Key Strikes: Heavy put open interest at $300, call walls at $300

Market Context:
- Price is pinned exactly at the gamma flip point
- Very low gamma concentration suggests minimal dealer positioning
- Positive net GEX but near zero total gamma indicates regime transition

QUESTION: Analyze the market mechanics using the WHO forces WHOM to do WHAT framework.

WHO: Identify the key market participant taking action
WHOM: Identify who is being forced to respond
WHAT: Describe the specific forced action that will occur

Provide your analysis with confidence level (0-100)."""

        # Get response from LLM
        response = await llm.interpret_mechanics_async(test_prompt)

        print(f"✅ {model_name} Response:")
        print(f"Response type: {type(response)}")
        print(f"Response: {response}")

        # Save result
        result = {
            "model": model_name,
            "event": "covid_crash_2020_obfuscated",
            "prompt": test_prompt,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }

        # Save to file
        output_dir = Path("reports/model_testing")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{model_name.replace('-', '_')}_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"💾 Saved: {output_file}")

        return result

    except Exception as e:
        print(f"❌ {model_name} failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"model": model_name, "error": str(e)}

async def main():
    """Test each model individually."""
    models_to_test = ["gpt-5-mini"]  # Test GPT-5 mini

    print("🚀 Starting Simple Model Testing")
    print(f"🔬 Models: {', '.join(models_to_test)}")

    all_results = []

    for model in models_to_test:
        try:
            result = await test_single_model(model)
            all_results.append(result)
        except Exception as e:
            print(f"❌ Failed to test {model}: {e}")

    print(f"\n✅ Completed testing {len(all_results)} models")

if __name__ == "__main__":
    asyncio.run(main())