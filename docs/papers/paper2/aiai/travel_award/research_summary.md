# Research Summary and Benefits Statement

## Validating LLM Structural Reasoning: Detecting Persistent Market Regimes Through Temporal Obfuscation

**Christopher Regan**, PhD Candidate, College of Computing and Software Engineering, Kennesaw State University

**Conference**: 22nd IFIP International Conference on Artificial Intelligence Applications and Innovations (AIAI 2026), July 16--19, 2026, Chania, Crete, Greece (Virtual Participation)

---

### Research Summary

Large language models (LLMs) have demonstrated remarkable reasoning capabilities, but a critical challenge remains: distinguishing genuine structural reasoning from memorization of training data. This distinction is essential for deploying LLMs in specialized domains such as financial analysis, medical diagnostics, and scientific research.

This research introduces **temporal obfuscation testing**, a validation methodology that strips identifying information---dates, ticker symbols, and contextual markers---from input data, forcing LLMs to reason purely from numerical structure. We apply this framework to financial market microstructure, specifically detecting persistent dealer gamma exposure (GEX) regimes from 30-day options market time series.

Our five-phase validation encompasses 2,221 evaluations (1,412 real market windows and 809 synthetic controls) spanning six years of market data (2020--2025). Key findings include:

- **Strong discrimination**: 69.1 percentage point separation between persistent regimes (81.2% detection in 2024) and fragmented markets (12.1% in 2020), with effect size phi = 0.672 (p < 0.0001)
- **Zero false positives**: 0% false positive rate on transitional and low-magnitude synthetic controls, confirming the framework enforces genuine structural criteria
- **Structural market shift**: Detection rates track the adoption of zero-days-to-expiration (0DTE) options, rising from 3.7% (2021) to 100% (2024--2025), with GEX magnitude growing 360% from $5B to $23B
- **High reasoning quality**: 98% mechanical accuracy across 50 manually reviewed LLM responses, with confidence scores significantly correlated to regime quality

The temporal obfuscation methodology is domain-agnostic and generalizable. By removing identifying markers and preserving only structural patterns, it addresses training data contamination concerns applicable to any specialized LLM deployment---from medical time series analysis to climate data interpretation to industrial anomaly detection.

### Benefits of Conference Attendance

Presenting this research at AIAI 2026 directly supports the successful completion of my doctoral degree in several ways:

1. **Dissertation validation**: This paper constitutes a core chapter of my dissertation. Peer review and audience feedback from the IFIP AI research community will strengthen the final dissertation, particularly regarding the generalizability claims of temporal obfuscation testing.

2. **Publication in Springer LNCS proceedings**: Accepted papers are published in Springer's Lecture Notes in Computer Science series, providing a high-quality, peer-reviewed publication essential for my academic record and dissertation defense.

3. **Research community engagement**: AIAI 2026 brings together researchers working on AI applications and innovations across domains. Engaging with this community will provide critical perspectives on extending the temporal obfuscation framework beyond financial markets---a key future direction identified in the paper.

4. **Professional development**: Virtual presentation at an international IFIP conference develops skills in communicating complex technical work to a broad AI audience, a competency essential for my post-doctoral career in AI research.

5. **Interdisciplinary feedback**: The conference's focus on AI applications across diverse domains (healthcare, manufacturing, finance) will provide insights into how temporal obfuscation testing could be adapted for other specialized domains, directly informing future dissertation work.

This research represents original doctoral work conducted under the supervision of Dr. Ying Xie at Kennesaw State University's College of Computing and Software Engineering.
