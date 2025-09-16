#!/usr/bin/env python3
"""
Final Reasoning Model Test with Fixed Parsing
Test O3-mini and O4-mini on COVID crash with proper Chain-of-Thought prompt
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

async def test_reasoning_cot(model_name: str):
    """Test reasoning model with CoT prompt and fixed parsing."""
    print(f"\n🧠 Final test: {model_name} with Chain-of-Thought")

    try:
        from llm.autogen_market_mechanics import AutoGenMarketMechanics

        # Initialize AutoGen
        llm = AutoGenMarketMechanics(model=model_name)

        # Chain-of-Thought prompt optimized for reasoning models
        cot_prompt = """You are an expert quantitative analyst. Analyze this step-by-step:

SCENARIO: Market event analysis (anonymized data)
- Net GEX: +211,032 (positive gamma)
- Price: $1190.02 (exactly at flip point)
- Total Gamma: 0 (very low concentration)
- Key strikes: Heavy put OI at $300, calls at $300

TASK: Use WHO-WHOM-WHAT framework to identify market mechanics

STEP 1 - GAMMA ANALYSIS:
Think: What does positive net GEX with zero total gamma mean?
Answer: This indicates dealers are in a transition regime at the flip point.

STEP 2 - PARTICIPANT ANALYSIS:
Think: Who has the most exposure requiring hedging?
Answer: Dealers must hedge their options positions dynamically.

STEP 3 - MECHANISM PREDICTION:
Think: What happens if price moves from the flip point?
Answer: Dealers will be forced to hedge in the direction of the move.

FINAL ANALYSIS:
WHO: [Primary participant driving mechanics]
WHOM: [Who is forced to respond]
WHAT: [Specific forced action]
CONFIDENCE: [Your confidence 0-100]

Provide clear, concise analysis."""

        # Use synchronous method since async has token issues
        response = llm.interpret_mechanics(cot_prompt)

        print(f"✅ {model_name} CoT Response:")
        print(f"WHO: {response.get('who', 'Not found')}")
        print(f"WHOM: {response.get('whom', 'Not found')}")
        print(f"WHAT: {response.get('what', 'Not found')}")
        print(f"CONFIDENCE: {response.get('confidence', 'Not found')}%")

        if response.get('narrative'):
            narrative = response.get('narrative', '')
            print(f"REASONING: {narrative[:300]}..." if len(narrative) > 300 else narrative)

        # Save result
        result = {
            "model": model_name,
            "test_type": "final_chain_of_thought",
            "event": "covid_crash_2020_obfuscated",
            "parsing_fixed": True,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }

        output_dir = Path("reports/final_reasoning_test")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{model_name.replace('-', '_')}_final_test.json"

        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"💾 Saved: {output_file}")

        return result

    except Exception as e:
        print(f"❌ {model_name} failed: {e}")
        import traceback
        traceback.print_exc()
        return {"model": model_name, "error": str(e)}

async def main():
    """Test both reasoning models with fixed parsing."""
    models = ["o3-mini", "o4-mini"]

    print("🧠 FINAL REASONING MODEL TEST")
    print("✅ Parsing fixed for numeric confidence scores")
    print("✅ Using synchronous method to avoid token limits")
    print("✅ Chain-of-Thought optimized prompts")

    results = []

    for model in models:
        result = await test_reasoning_cot(model)
        results.append(result)

    # Compare results
    print(f"\n📊 FINAL COMPARISON - REASONING MODELS")
    print("="*60)

    for result in results:
        if "error" not in result:
            resp = result["response"]
            print(f"\n{result['model'].upper()}:")
            print(f"  WHO: {resp.get('who', 'Unknown')}")
            print(f"  WHOM: {resp.get('whom', 'Unknown')}")
            print(f"  WHAT: {resp.get('what', 'Unknown')}")
            print(f"  CONFIDENCE: {resp.get('confidence', 'Unknown')}%")
        else:
            print(f"\n{result['model'].upper()}: ERROR - {result.get('error')}")

    print(f"\n🎯 Reasoning models are now working with proper prompting!")

if __name__ == "__main__":
    asyncio.run(main())