# Cover letter (draft)

TODO(authors): journal and editor, date. The venue is not chosen; keep the MDPI class until it is.

Dear Editors,

We submit "Reproducing an LLM Evaluation After Its Hosted Model Is Retired: Open-Weights Models on Stored Requests" for consideration
as a research article.

An evaluation of a language model can be repeated only while its model can be called. We take an evaluation whose hosted model has
been retired, a deterministic three-threshold rule on windows of obfuscated daily SPY gamma exposure that the prompt states, and ask
whether it can be reproduced with open-weights models run locally at pinned revisions on the stored requests. Three models of three
developers (gpt-oss-20b, Llama 3.1 8B, Qwen3-8B) answered seven arms each. gpt-oss-20b reproduces the stored verdicts and follows
the rule; Qwen3-8B follows the rule where it answers but leaves 8.8% of the windows unanswered, so its rate is reported as bounds;
Llama 3.1 8B with the verdict first detects almost every window. Agreement with the rule shows that a model applies stated criteria;
we do not claim more. TODO(runs): one sentence on the reasoning-first and temperature-0 runs once they are stored.

This paper is a companion of a second manuscript by the same authors, which re-runs the underlying test on complete inputs and
bridges the retired model to its hosted successor ("Persistent Dealer-Gamma Regimes Under Temporal Obfuscation: A Re-Run on
Complete Inputs with a Controlled LLM Re-Test", in preparation). That manuscript owns the input series, the re-run and the bridge;
this paper cites them and reports only the open-weights comparison. The two papers share one data deposit (Zenodo, DOI TODO(authors)).
The earlier publications on which both build are cited in the text.

All code, condensed result tables and the figure scripts are in the repository named in the Data Availability Statement; every
request and answer of the open-weights runs is in the deposit. No part of the manuscript is under consideration elsewhere.
TODO(authors): confirm, and state the AI-assistance disclosure as in the manuscript.

Sincerely,
Christopher Regan and Ying Xie, Kennesaw State University
