# Cover letter (draft)

TODO(authors): date, and whether this paper goes to the same Special Issue as Paper A or to the regular Electronics list (article type: research article).

Dear Editors of *Electronics*,

We submit "Reproducing an LLM Evaluation After Its Hosted Model Is Retired: Open-Weights Models on Stored Requests" by Christopher Regan
and Ying Xie (Kennesaw State University) for consideration in *Electronics* as a research article. It is the companion of a second manuscript
that we submit to the same journal at the same time (see below).

An evaluation of a language model can be repeated only while its model can be called. We take an evaluation whose hosted model has
been retired, a deterministic three-threshold rule on windows of obfuscated daily SPY gamma exposure that the prompt states, and ask
whether it can be reproduced with open-weights models run locally at pinned revisions on the stored requests. Three models of three
developers (gpt-oss-20b, Llama 3.1 8B, Qwen3-8B) answered seven arms each. gpt-oss-20b reproduces the stored verdicts and follows
the rule; Qwen3-8B follows the rule where it answers (98.7% of the answered windows of the complete series, 88.5% of all of them if the unanswered ones count as errors) but leaves 8.8% of the windows unanswered, so its rate is reported as bounds;
Llama 3.1 8B with the verdict first detects almost every window. Agreement with the rule shows that a model applies stated criteria;
we do not claim more. With the reasoning first Llama 3.1 8B no longer answers yes to every window but still does not follow the rule, and temperature 0 changes neither the gpt-oss-20b nor the Llama result on the published inputs.

**Relation to the companion submission (Paper A).** Paper A, "Persistent Dealer-Gamma Regimes Under Temporal Obfuscation: A Re-Run on
Inputs with Both Option Legs and a Rule-Following Test of a Current LLM", is submitted to *Electronics* as well. Paper A reports the
provenance of the input series, the re-run of the regime test on the complete inputs, and the bridge between the retired model (o4-mini)
and its hosted successor (gpt-6-luna). This paper reports only the open-weights comparison: gpt-oss-20b, Llama 3.1 8B and Qwen3-8B at
pinned revisions on the stored requests, their agreement with the rule, the stored o4-mini verdicts and gpt-6-luna, the unanswered
windows and bounds, the departures from the rule, the effect of the answer order and of temperature 0, and tokens and GPU time. Numbers of
Paper A appear here only as cited context or as labelled reference columns ("Paper A"), never as results of this paper, and none of the
open-weights results appears in Paper A, so nothing is reported as new in both. The two papers share one data deposit (Zenodo, DOI TODO(authors)).
The earlier publications on which both build are cited in the text.

All code, condensed result tables and the figure scripts are in the repository named in the Data Availability Statement; every
request and answer of the open-weights runs is in the deposit. No part of the manuscript is under consideration elsewhere.
As stated in the Acknowledgments, the authors used Claude Code to write and run the analysis code, to draft and revise the text and to
check the manuscript against the stored results; they decided the design, the runs and analyses reported and the conclusions, and they
take full responsibility for the content. TODO(authors): confirm this paragraph.

Sincerely,
Christopher Regan and Ying Xie, Kennesaw State University
