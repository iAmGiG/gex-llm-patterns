#!/usr/bin/env python3
"""
Reasoning Model Testing Script
Tests O3-mini and O4-mini with Chain-of-Thought optimized prompts
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

async def test_reasoning_model(model_name: str):
    """Test reasoning model with CoT-optimized prompt."""
    print(f"\n🧠 Testing {model_name} with Chain-of-Thought prompt")

    try:
        # Import here to avoid circular imports
        from llm.autogen_market_mechanics import AutoGenMarketMechanics

        # Initialize AutoGen with specific model
        llm = AutoGenMarketMechanics(model=model_name)

        # Reasoning-optimized prompt with explicit role and step-by-step thinking
        reasoning_prompt = """You are an expert quantitative analyst specializing in options market microstructure and dealer positioning dynamics.

ROLE DEFINITION:
- Expert in gamma exposure (GEX) analysis and dealer hedging mechanics
- Specialist in identifying forced hedging flows and market participant interactions
- Your job is to reason step-by-step through market mechanics using the WHO-WHOM-WHAT framework

ANALYTICAL FRAMEWORK:
WHO = The market participant initiating the action
WHOM = The participant being forced to respond
WHAT = The specific forced action that creates market impact

DATA PROVIDED (ANONYMIZED TO PREVENT BIAS):
Date: Day T+0 (market event date)
Gamma Exposure Metrics:
- Net GEX: +211,032 (positive gamma environment)
- Flip Point: $1190.02
- Current Spot Price: $1190.02 (exactly at flip point)
- Total Gamma: 0 (unusually low)
- Gamma Concentration: 0% (very dispersed)
- Key Levels: Heavy put OI at $300 strike, call walls at $300 strike

MARKET CONTEXT CLUES:
- Price is pinned exactly at the calculated flip point
- Despite positive net GEX, total gamma is near zero
- Very low concentration suggests minimal large positioning
- The $300 strikes are far from current price ($1190)

REASONING TASK:
Please think through this step-by-step:

STEP 1 - GAMMA REGIME ANALYSIS:
- What does "positive net GEX but zero total gamma" tell us about dealer positioning?
- What are the implications of price being exactly at the flip point?
- How does low gamma concentration affect dealer hedging requirements?

STEP 2 - PARTICIPANT IDENTIFICATION:
- WHO are the key market participants in this scenario?
- What positions might they hold given the GEX profile?
- Who has the most risk/exposure that requires hedging?

STEP 3 - FORCED FLOW ANALYSIS:
- WHOM will be forced to act as price moves from the flip point?
- WHAT specific actions will they be forced to take?
- How do the hedging flows amplify or dampen price movements?

STEP 4 - MECHANICAL PREDICTION:
- If price moves up from flip point, what happens?
- If price moves down from flip point, what happens?
- What is the most likely scenario given current positioning?

STEP 5 - SYNTHESIS:
Based on your step-by-step analysis, provide:
- WHO: The primary participant driving the mechanics
- WHOM: Who is being forced to respond
- WHAT: The specific forced action
- CONFIDENCE: Your confidence level (0-100) in this analysis

Think through each step carefully and show your reasoning process."""

        # Get response from LLM
        response = await llm.interpret_mechanics_async(reasoning_prompt)

        print(f"✅ {model_name} Chain-of-Thought Response:")
        print(f"Response type: {type(response)}")

        # Extract and display key parts
        if isinstance(response, dict):
            print(f"WHO: {response.get('who', 'Not specified')}")
            print(f"WHOM: {response.get('whom', 'Not specified')}")
            print(f"WHAT: {response.get('what', 'Not specified')}")
            print(f"Confidence: {response.get('confidence', 'Not specified')}%")

            if response.get('narrative'):
                print(f"Reasoning: {response.get('narrative', '')[:200]}..." if len(response.get('narrative', '')) > 200 else response.get('narrative', ''))

        # Save result
        result = {
            "model": model_name,
            "test_type": "chain_of_thought_reasoning",
            "event": "covid_crash_2020_obfuscated",
            "prompt_type": "reasoning_optimized",
            "prompt": reasoning_prompt,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }

        # Save to file
        output_dir = Path("reports/reasoning_model_testing")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{model_name.replace('-', '_')}_cot_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

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
    """Test reasoning models with improved prompts."""
    reasoning_models = ["o3-mini", "o4-mini"]  # Test both reasoning models

    print("🧠 Starting Chain-of-Thought Reasoning Model Testing")
    print(f"🔬 Models: {', '.join(reasoning_models)}")
    print("💰 Estimated cost: ~$0.004 total")

    all_results = []

    for model in reasoning_models:
        try:
            result = await test_reasoning_model(model)
            all_results.append(result)

            # Brief pause between tests
            await asyncio.sleep(1)

        except Exception as e:
            print(f"❌ Failed to test {model}: {e}")

    # Generate comparison
    print(f"\n📊 REASONING MODEL COMPARISON")
    print("="*50)

    for result in all_results:
        if "error" not in result and isinstance(result.get("response"), dict):
            response = result["response"]
            print(f"\n{result['model'].upper()}:")
            print(f"  WHO: {response.get('who', 'Unknown')}")
            print(f"  WHOM: {response.get('whom', 'Unknown')}")
            print(f"  WHAT: {response.get('what', 'Unknown')}")
            print(f"  Confidence: {response.get('confidence', 'Unknown')}%")
        else:
            print(f"\n{result['model'].upper()}: FAILED - {result.get('error', 'Unknown error')}")

    print(f"\n✅ Completed reasoning model testing")

if __name__ == "__main__":
    asyncio.run(main())