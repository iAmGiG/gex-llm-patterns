#!/usr/bin/env python3
"""
Generate slide-friendly system architecture diagram with complete data flow.

Features:
- Vertical/hierarchical layout (not linear bar)
- Shows Alpha Vantage API as data source
- Includes caching system (DB check)
- Better for presentation slides
"""

import graphviz


def generate_layered_architecture():
    """
    Generate layered architecture diagram showing complete system.

    Layout: Top-to-bottom with multiple parallel flows
    """

    dot = graphviz.Digraph(
        comment='Complete System Architecture',
        format='png',
        engine='dot'
    )

    # Graph attributes for vertical layout
    dot.attr(
        rankdir='TB',  # Top to bottom
        size='12,14',
        dpi='300',
        fontname='Arial',
        nodesep='0.6',
        ranksep='0.8',
        bgcolor='white'
    )

    # Define node styles
    dot.attr('node',
             fontname='Arial',
             fontsize='12',
             style='filled,rounded',
             shape='box'
             )

    # ============ LAYER 1: DATA SOURCES ============
    with dot.subgraph(name='cluster_sources') as c:
        c.attr(label='Data Sources', fontsize='14',
               style='dashed', color='gray')

        c.node('api',
               'Alpha Vantage API\n\nOptions Chain Data\n(SPY Calls + Puts)',
               fillcolor='#E8F4F8',
               color='#2E86C1',
               penwidth='2'
               )

        c.node('cache',
               'Cache System\n(SQLite DB)\n\nHistorical GEX\nStored Results',
               fillcolor='#E8F4F8',
               color='#2E86C1',
               penwidth='2'
               )

    # ============ LAYER 2: DATA PROCESSING ============
    with dot.subgraph(name='cluster_processing') as c:
        c.attr(label='Data Processing', fontsize='14',
               style='dashed', color='gray')

        c.node('fetch',
               'Data Retrieval\n\n1. Check Cache (DB)\n2. Fetch if missing\n3. Store results',
               fillcolor='#FEF5E7',
               color='#D68910',
               penwidth='2'
               )

        c.node('gex',
               'GEX Calculator\n\nNet GEX\nCall/Put GEX\nFlip Point',
               fillcolor='#FEF5E7',
               color='#D68910',
               penwidth='2'
               )

    # ============ LAYER 3: OBFUSCATION ============
    dot.node('obfuscate',
             'Data Obfuscator\n\n❌ Remove: Dates, Tickers, Events\n✓ Preserve: GEX values, Spot price\n\nFormat: "Day T+0", "INDEX_1"',
             fillcolor='#FADBD8',
             color='#C0392B',
             penwidth='2'
             )

    # ============ LAYER 4: LLM ANALYSIS ============
    with dot.subgraph(name='cluster_llm') as c:
        c.attr(label='LLM Agent', fontsize='14',
               style='dashed', color='#7D3C98')

        c.node('llm_tool',
               'Tool Calling\n\nGPT-4o-mini\n(Cost-efficient)',
               fillcolor='#E8DAEF',
               color='#7D3C98',
               penwidth='2',
               shape='ellipse'
               )

        c.node('llm_reason',
               'Reasoning\n\no3-mini\n(Cost-optimized)',
               fillcolor='#E8DAEF',
               color='#7D3C98',
               penwidth='2',
               shape='ellipse'
               )

        c.node('llm_framework',
               'WHO→WHOM→WHAT\nFramework\n\nCausal Chain\nIdentification',
               fillcolor='#D5DBDB',
               color='#566573',
               penwidth='2'
               )

    # ============ LAYER 5: VALIDATION ============
    with dot.subgraph(name='cluster_validation') as c:
        c.attr(label='Validation Pipeline', fontsize='14',
               style='dashed', color='gray')

        c.node('outcome',
               'Outcome Calculator\n\nForward Returns\nRealized Vol\nPrediction Check',
               fillcolor='#D5F4E6',
               color='#229954',
               penwidth='2'
               )

        c.node('validator',
               'Statistical Validator\n\nDetection Rate: 71.5%\nAccuracy: 91.2%\n✓ Mechanical (>60%)',
               fillcolor='#AED6F1',
               color='#1F618D',
               penwidth='2'
               )

    # ============ EDGES - DATA FLOW ============

    # Data source flows
    dot.edge('api', 'fetch', label='Real-time\nAPI calls',
             fontsize='10', color='#2E86C1')
    dot.edge('cache', 'fetch', label='Check\ncache first',
             fontsize='10', color='#2E86C1', style='dashed')

    # Processing flow
    dot.edge('fetch', 'gex', label='Options\nchain', fontsize='10')
    dot.edge('fetch', 'cache', label='Store\nresults',
             fontsize='10', style='dashed', dir='back')

    # GEX to obfuscation
    dot.edge('gex', 'obfuscate', label='GEX\nmetrics', fontsize='10')

    # Obfuscation to LLM
    dot.edge('obfuscate', 'llm_tool', label='Obfuscated\ndata', fontsize='10')
    dot.edge('obfuscate', 'llm_reason',
             label='Obfuscated\ndata', fontsize='10')

    # LLM internal
    dot.edge('llm_tool', 'llm_framework', label='Function\ncalls',
             fontsize='10', style='dashed')
    dot.edge('llm_reason', 'llm_framework',
             label='Pattern\nanalysis', fontsize='10', style='dashed')

    # LLM to validation
    dot.edge('llm_framework', 'outcome',
             label='Pattern detection\n+ Predictions', fontsize='10')

    # Validation flow
    dot.edge('outcome', 'validator', label='Realized\noutcomes', fontsize='10')

    # Add overall title
    dot.attr(label='\\n\\nPattern Detection System Architecture\\nFull Pipeline with Caching',
             labelloc='t',
             fontsize='18',
             fontname='Arial Bold'
             )

    # Save PNG for slides
    output_path = 'docs/presentations/oct22_research/diagrams/system_architecture_layered'
    dot.render(output_path, cleanup=True)
    print(f"✅ Generated: {output_path}.png (layered, slide-friendly)")

    return dot


def generate_compact_flow():
    """
    Generate compact flowchart showing key components only.

    Better for single slide presentation.
    """

    dot = graphviz.Digraph(
        comment='Compact System Flow',
        format='png',
        engine='dot'
    )

    # Compact layout
    dot.attr(
        rankdir='TB',
        size='10,12',
        dpi='300',
        fontname='Arial Bold',
        bgcolor='transparent',
        nodesep='0.7',
        ranksep='1.0'
    )

    dot.attr('node',
             fontname='Arial Bold',
             fontsize='13',
             style='filled,rounded',
             shape='box',
             height='0.9',
             width='2.5'
             )

    # Main flow (5 key components)
    dot.node('source',
             '📊 Data Source\n\nAlpha Vantage API\n+ Cache (SQLite)',
             fillcolor='#E8F4F8',
             color='#2E86C1',
             penwidth='3'
             )

    dot.node('process',
             '⚙️ GEX Processing\n\nCalculate Gamma\nObfuscate Data',
             fillcolor='#FEF5E7',
             color='#D68910',
             penwidth='3'
             )

    dot.node('llm',
             '🤖 LLM Analysis\n\nGPT-4o-mini + o3-mini\nPattern Detection',
             fillcolor='#E8DAEF',
             color='#7D3C98',
             penwidth='3'
             )

    dot.node('validate',
             '✓ Validation\n\nOutcomes + Stats\n71.5% Detection',
             fillcolor='#D5F4E6',
             color='#229954',
             penwidth='3'
             )

    dot.node('results',
             '📈 Results\n\n91.2% Accuracy\nMechanical Pattern',
             fillcolor='#AED6F1',
             color='#1F618D',
             penwidth='3'
             )

    # Flow edges
    dot.edge('source', 'process', penwidth='4',
             color='#34495E', arrowsize='1.5')
    dot.edge('process', 'llm', penwidth='4', color='#34495E', arrowsize='1.5')
    dot.edge('llm', 'validate', penwidth='4', color='#34495E', arrowsize='1.5')
    dot.edge('validate', 'results', penwidth='4',
             color='#34495E', arrowsize='1.5')

    # Save
    output_path = 'docs/presentations/oct22_research/diagrams/system_flow_compact'
    dot.render(output_path, cleanup=True)
    print(f"✅ Generated: {output_path}.png (compact, 5-component flow)")

    return dot


def generate_detailed_with_swim_lanes():
    """
    Generate detailed diagram with swim lanes showing different system layers.
    """

    dot = graphviz.Digraph(
        comment='System Architecture - Swim Lanes',
        format='png',
        engine='dot'
    )

    dot.attr(
        rankdir='LR',  # Left to right for swim lanes
        size='16,10',
        dpi='300',
        fontname='Arial',
        compound='true',  # Allow edges between clusters
        bgcolor='white'
    )

    # ============ SWIM LANE 1: DATA LAYER ============
    with dot.subgraph(name='cluster_data') as c:
        c.attr(
            label='Data Layer',
            fontsize='14',
            style='filled',
            color='lightgray',
            fillcolor='#F8F9F9'
        )

        c.node('api_src', 'Alpha Vantage\nAPI',
               fillcolor='#AED6F1', shape='cylinder')
        c.node('cache_db', 'Cache DB\n(SQLite)',
               fillcolor='#AED6F1', shape='cylinder')
        c.node('fetch_data', 'Data Fetcher\n\n1. Check cache\n2. API if needed',
               fillcolor='#D6EAF8')

    # ============ SWIM LANE 2: PROCESSING LAYER ============
    with dot.subgraph(name='cluster_proc') as c:
        c.attr(
            label='Processing Layer',
            fontsize='14',
            style='filled',
            color='lightgray',
            fillcolor='#FEF9E7'
        )

        c.node('gex_calc', 'GEX\nCalculator', fillcolor='#FCF3CF')
        c.node('obfuscate_data', 'Data\nObfuscator', fillcolor='#FCF3CF')

    # ============ SWIM LANE 3: AI LAYER ============
    with dot.subgraph(name='cluster_ai') as c:
        c.attr(
            label='AI Layer',
            fontsize='14',
            style='filled',
            color='lightgray',
            fillcolor='#F4ECF7'
        )

        c.node('llm_agent', 'LLM Agent\n\nGPT-4o-mini\n+ o3-mini',
               fillcolor='#E8DAEF')
        c.node('pattern_detect', 'Pattern\nDetection', fillcolor='#E8DAEF')

    # ============ SWIM LANE 4: VALIDATION LAYER ============
    with dot.subgraph(name='cluster_val') as c:
        c.attr(
            label='Validation Layer',
            fontsize='14',
            style='filled',
            color='lightgray',
            fillcolor='#E8F8F5'
        )

        c.node('calc_outcome', 'Outcome\nCalculator', fillcolor='#D5F4E6')
        c.node('stat_valid', 'Statistical\nValidator', fillcolor='#D5F4E6')
        c.node('results_out', 'Results\n\n71.5% Det\n91.2% Acc',
               fillcolor='#ABEBC6', shape='note')

    # ============ DATA FLOW EDGES ============
    dot.edge('api_src', 'fetch_data', label='API call')
    dot.edge('cache_db', 'fetch_data', label='check', style='dashed')
    dot.edge('fetch_data', 'cache_db', label='store',
             style='dashed', dir='back')

    dot.edge('fetch_data', 'gex_calc',
             label='options data', lhead='cluster_proc')
    dot.edge('gex_calc', 'obfuscate_data', label='GEX')

    dot.edge('obfuscate_data', 'llm_agent',
             label='obfuscated', lhead='cluster_ai')
    dot.edge('llm_agent', 'pattern_detect', label='analysis')

    dot.edge('pattern_detect', 'calc_outcome',
             label='predictions', lhead='cluster_val')
    dot.edge('calc_outcome', 'stat_valid', label='outcomes')
    dot.edge('stat_valid', 'results_out', label='metrics')

    # Save
    output_path = 'docs/presentations/oct22_research/diagrams/system_architecture_swimlanes'
    dot.render(output_path, cleanup=True)
    print(f"✅ Generated: {output_path}.png (swim lanes, detailed)")

    return dot


if __name__ == '__main__':
    print("Generating slide-friendly system architecture diagrams...\n")

    print("📊 Version 1: Layered Architecture (vertical, detailed)")
    generate_layered_architecture()
    print()

    print("📊 Version 2: Compact Flow (5 components, simple)")
    generate_compact_flow()
    print()

    print("📊 Version 3: Swim Lanes (horizontal, by system layer)")
    generate_detailed_with_swim_lanes()
    print()

    print("✅ All slide-friendly diagrams generated!")
    print("📁 Output: docs/presentations/oct22_research/diagrams/")
    print("\nRecommendation:")
    print("  - For single slide: system_flow_compact.png")
    print("  - For detailed slide: system_architecture_layered.png")
    print("  - For technical audience: system_architecture_swimlanes.png")
