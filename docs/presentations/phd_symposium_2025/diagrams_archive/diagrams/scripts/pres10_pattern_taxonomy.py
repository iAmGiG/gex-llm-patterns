#!/usr/bin/env python3
"""
Generate pattern taxonomy diagram for Oct 22 presentation.

Shows 3-level hierarchy:
- Level 1: Pattern Types (Structural, Statistical, Narrative)
- Level 2: Pattern Categories
- Level 3: Specific Patterns

Accurate information:
- Structural patterns: Gamma Positioning, Stock Pinning, 0DTE Hedging
- All three patterns are VALIDATED (100% detection, 87-98% accuracy)
"""

import graphviz


def generate_pattern_taxonomy():
    """Generate 3-level pattern taxonomy hierarchy."""

    dot = graphviz.Digraph(comment="Pattern Taxonomy", format="png", engine="dot")

    # Graph attributes for hierarchical layout
    dot.attr(
        rankdir="TB",  # Top to bottom
        size="12,10",
        dpi="300",
        fontname="Arial",
        ranksep="1.2",
        nodesep="0.8",
        bgcolor="white",
    )

    # Default node styling
    dot.attr("node", fontname="Arial", fontsize="12", style="filled,rounded", shape="box")

    # ============ LEVEL 0: ROOT ============
    dot.node(
        "root",
        "GEX Pattern Taxonomy\n\nClassification by Detection Mechanism",
        fillcolor="#D5DBDB",
        color="#566573",
        penwidth="3",
        fontsize="14",
        fontname="Arial Bold",
        shape="box",
        style="rounded,filled",
    )

    # ============ LEVEL 1: PATTERN TYPES ============

    # Structural (mechanical, constraint-based)
    dot.node(
        "structural",
        "STRUCTURAL\n\n✅ Mechanical Constraints\n✅ Regulatory/Physical Limits\n✅ Obfuscation-Resistant",
        fillcolor="#D5F4E6",
        color="#229954",
        penwidth="3",
        width="2.5",
        height="1.2",
    )

    # Statistical (data-driven patterns)
    dot.node(
        "statistical",
        "STATISTICAL\n\n📊 Data-Driven Patterns\n📊 Historical Correlations\n⚠️ Context-Dependent",
        fillcolor="#FEF5E7",
        color="#D68910",
        penwidth="3",
        width="2.5",
        height="1.2",
    )

    # Narrative (requires temporal context)
    dot.node(
        "narrative",
        "NARRATIVE\n\n❌ Time-Dependent\n❌ Requires Context\n❌ Obfuscation-Vulnerable",
        fillcolor="#FADBD8",
        color="#C0392B",
        penwidth="3",
        width="2.5",
        height="1.2",
    )

    # ============ LEVEL 2: VALIDATED STRUCTURAL PATTERNS ============

    with dot.subgraph(name="cluster_validated") as c:
        c.attr(label="Validated Patterns (2024)", fontsize="13", style="dashed", color="#229954", penwidth="2")

        c.node(
            "gamma_pos",
            "Gamma Positioning\n\n🎯 Detection: 100%\n✓ Accuracy: 96.2% (Q1)\n\nDealer Constraint:\nDelta neutrality mandate",
            fillcolor="#ABEBC6",
            color="#229954",
            penwidth="2",
            width="2.2",
        )

        c.node(
            "stock_pin",
            "Stock Pinning\n\n🎯 Detection: 100%\n✓ Accuracy: 86.5% (Q1)\n\nDealer Constraint:\nGamma concentration at strikes",
            fillcolor="#ABEBC6",
            color="#229954",
            penwidth="2",
            width="2.2",
        )

        c.node(
            "dte_hedge",
            "0DTE Hedging\n\n🎯 Detection: 100%\n✓ Accuracy: 90.4% (Q1)\n\nDealer Constraint:\nExponential time decay",
            fillcolor="#ABEBC6",
            color="#229954",
            penwidth="2",
            width="2.2",
        )

    # ============ LEVEL 2: STATISTICAL PATTERNS (NOT VALIDATED) ============

    dot.node(
        "volume_anom",
        "Volume Anomaly\n\n⏳ Not Yet Tested\n\nPattern:\nUnusual volume spikes",
        fillcolor="#FAE5D3",
        color="#D68910",
        penwidth="2",
        width="2.0",
        style="rounded,filled,dashed",
    )

    # ============ LEVEL 2: NARRATIVE PATTERNS (FAILED) ============

    with dot.subgraph(name="cluster_failed") as c:
        c.attr(
            label="Failed Validation (Obfuscation Test)", fontsize="13", style="dashed", color="#C0392B", penwidth="2"
        )

        c.node(
            "friday_330",
            "Friday 3:30 PM Squeeze\n\n❌ Failed\n\nRequires:\nKnowing day/time context",
            fillcolor="#F5B7B1",
            color="#C0392B",
            penwidth="2",
            width="2.0",
        )

        c.node(
            "dealer_trap",
            "Dealer Trap Setup\n\n❌ Failed\n\nRequires:\nTemporal context awareness",
            fillcolor="#F5B7B1",
            color="#C0392B",
            penwidth="2",
            width="2.0",
        )

    # ============ EDGES - HIERARCHY ============

    # Root to Level 1
    dot.edge("root", "structural", penwidth="2", color="#229954")
    dot.edge("root", "statistical", penwidth="2", color="#D68910")
    dot.edge("root", "narrative", penwidth="2", color="#C0392B")

    # Structural to validated patterns
    dot.edge("structural", "gamma_pos", penwidth="2", color="#229954")
    dot.edge("structural", "stock_pin", penwidth="2", color="#229954")
    dot.edge("structural", "dte_hedge", penwidth="2", color="#229954")

    # Statistical to volume anomaly
    dot.edge("statistical", "volume_anom", penwidth="2", color="#D68910", style="dashed")

    # Narrative to failed patterns
    dot.edge("narrative", "friday_330", penwidth="2", color="#C0392B")
    dot.edge("narrative", "dealer_trap", penwidth="2", color="#C0392B")

    # Add title
    dot.attr(
        label="\\n\\nPattern Taxonomy: Classification by Detection Mechanism\\n(Structural patterns pass obfuscation testing)",
        labelloc="b",
        fontsize="12",
        fontname="Arial",
    )

    # Save PNG for slides
    output_path = "docs/presentations/oct22_research/diagrams/pattern_taxonomy"
    dot.render(output_path, cleanup=True)
    print(f"✅ Generated: {output_path}.png (pattern taxonomy, hierarchical)")

    return dot


if __name__ == "__main__":
    print("Generating pattern taxonomy diagram...\n")
    generate_pattern_taxonomy()
    print("\n✅ Pattern taxonomy diagram complete!")
    print("📁 Output: docs/presentations/oct22_research/diagrams/pattern_taxonomy.png")
