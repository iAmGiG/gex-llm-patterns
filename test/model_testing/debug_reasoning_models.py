#!/usr/bin/env python3
"""
Debug Reasoning Models - Check Raw API Responses
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

async def debug_raw_response(model_name: str):
    """Debug what's actually coming back from reasoning models."""
    print(f"\n🔍 Debugging {model_name} raw response")

    try:
        from llm.autogen_market_mechanics import AutoGenMarketMechanics

        # Initialize AutoGen
        llm = AutoGenMarketMechanics(model=model_name)

        # Simple test prompt
        simple_prompt = """You are a financial analyst.

Analyze this options data:
- Net GEX: +211,032
- Price: $1190

Question: What does positive GEX mean for dealer hedging?

Please provide:
WHO: [market participant]
WHAT: [action they take]
CONFIDENCE: [0-100]
"""

        print(f"Testing with simple prompt...")

        # Call the raw interpret_mechanics_async method
        response = await llm.interpret_mechanics_async(simple_prompt)

        print(f"Raw response type: {type(response)}")
        print(f"Raw response content: {response}")

        # Try to see what the actual LLM returned before parsing
        # Let's also try the synchronous method
        sync_response = llm.interpret_mechanics(simple_prompt)
        print(f"Sync response: {sync_response}")

        # Try using generate method directly
        raw_generate = llm.generate(simple_prompt)
        print(f"Generate method: {raw_generate}")

        return {
            "model": model_name,
            "async_response": response,
            "sync_response": sync_response,
            "raw_generate": raw_generate
        }

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return {"model": model_name, "error": str(e)}

async def main():
    """Debug both reasoning models."""
    models = ["o3-mini", "o4-mini"]

    for model in models:
        result = await debug_raw_response(model)

        # Save debug info
        output_file = Path("reports") / f"debug_{model.replace('-', '_')}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"💾 Debug saved: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())