Prompt:

You will receive two uploaded files:
(1) The full text of a scientific sports/physiology paper.
(2) The AI-generated JSON analysis of that paper.

Your task is to evaluate how well the analysis reflects the actual paper. 
Be strict and rely only on the uploaded content.

Return ONLY a JSON object in the following format:

{
  "pmid": "<extract pmid from the JSON file>",
  "fidelity_score": 0-10,
  "hallucination_score": 0-10,
  "direction_accuracy_score": 0-10,
  "completeness_score": 0-10,
  "overall_rating": "<excellent|good|acceptable|poor|hallucinated>",
  "issues": [
    "list up to 3 key problems, max 12 words each"
  ]
}

Score definitions:
- fidelity_score: how closely the analysis matches the paper’s actual findings (10 = perfect).
- hallucination_score: absence of invented claims not found in the paper (10 = none).
- direction_accuracy_score: correctness of increase/decrease or up/downregulation directions (10 = perfect).
- completeness_score: coverage of key findings relevant to biomarkers, physiology, or outcomes (10 = complete).

Rating rules:
- 9–10 → excellent
- 7–8 → good
- 5–6 → acceptable
- 3–4 → poor
- 0–2 → hallucinated

Rules:
- Do NOT quote long passages.
- Do NOT output anything except the JSON object.
- Keep issues short and only include the most important mismatches.


Issue explantions:

A) Overinterpretation / Overclaiming
AI states findings more strongly than the paper.
Typical patterns:
Correlation phrased like causation
Secondary points treated as main findings
Context generalized beyond data
Mechanistic explanations overstated
Prognostic value overstated
“Beneficial” language not supported
Trends framed as solid effects
Category: overinterpretation

B) Not Measured / Invented Biomarkers
AI mentions biomarkers or effects not measured in the study
Typical patterns:
Biomarkers included that do not appear in the paper
Hypotheses treated as measured outcomes
External findings mixed in
Mechanistic pathways presented as results
Category: hallucinated_data

C) Incorrect or Unclear Direction
Up/Down direction is wrong or imprecise
Typical patterns:
↑ instead of ↓ or vice versa
Direction missing
Ambiguous effect descriptions
Narrative direction added without data
Category: direction_mismatch

D) Study Design Misrepresentation
AI misrepresents the study type or methodological constraints.
Typical patterns:
Review summarised like a single experiment
Observational study framed as interventional
Protocol treated as actual results
Prognostic strength overstated
Heterogeneous studies over-aggregate
Category: study_design_error

E) Missing Limitations / Missing Context
Important limitations or contextual constraints are omitted.
Typical patterns:
Small sample size not mentioned
Exploratory nature underemphasized
Conflicting evidence ignored
Broader context overstated
Non-sports papers framed as sports physiology
Category: missing_limitatons

F) Technical Detail Errors
Specific scientific details are inaccurate.
Typical patterns:
Incorrect biomarker cutoffs
Terminology mistakes
Statistical detail errors (tests, correlations)
Misstated numeric thresholds
Category: technical_error

G) Redundant / Irrelevant / Over-inclusion
AI includes unnecessary or unrelated content.
Typical patterns:
Findings from other studies inserted
Redundant descriptions
Irrelevant biological mechanisms
Unimportant effects overstated
Category: noise_or_redundancy
