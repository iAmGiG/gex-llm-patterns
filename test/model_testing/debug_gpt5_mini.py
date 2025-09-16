#!/usr/bin/env python3
"""
Debug GPT-5 Mini - Test Basic Functionality
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

async def debug_gpt5_basic():
    """Debug basic GPT-5 mini functionality."""
    print(f"\n🔍 Debug: GPT-5 mini basic functionality")

    try:
        from llm.autogen_market_mechanics import AutoGenMarketMechanics

        # Initialize AutoGen
        llm = AutoGenMarketMechanics(model="gpt-5-mini")

        # Very simple test
        basic_prompt = "What is 2 + 2?"

        print(f"Testing basic math...")

        # Test different methods
        print("\n1. Testing generate() method:")
        raw_generate = llm.generate(basic_prompt)
        print(f"Result: {raw_generate}")

        print("\n2. Testing interpret_mechanics() method:")
        mechanics_response = llm.interpret_mechanics(basic_prompt)
        print(f"Result: {mechanics_response}")

        # Test financial prompt
        financial_prompt = """What does positive gamma mean in options trading?

WHO: [key participant]
WHAT: [their action]
CONFIDENCE: [0-100]"""

        print("\n3. Testing simple financial prompt:")
        financial_response = llm.interpret_mechanics(financial_prompt)
        print(f"Result: {financial_response}")

        return {
            "basic_math": raw_generate,
            "mechanics_basic": mechanics_response,
            "financial_simple": financial_response
        }

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

async def main():
    """Debug GPT-5 mini."""
    print("🔍 GPT-5 MINI DEBUG")

    result = await debug_gpt5_basic()

    # Save debug info
    output_file = Path("reports") / "debug_gpt5_mini.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"💾 Debug saved: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())