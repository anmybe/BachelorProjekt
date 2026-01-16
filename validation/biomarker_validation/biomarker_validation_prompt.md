You will receive two files:
(1) The consolidated biomarker summary.
(2) The paper-level evidence for this biomarker.

Your task:
Evaluate how well the consolidated summary matches the findings of the underlying papers.
Be strict, concise, and fully evidence-based.

Return ONLY the following JSON:

{
  "biomarker": "<name>",
  "factual_accuracy_score": 0-10,
  "coverage_score": 0-10,
  "hallucination_score": 0-10,
  "direction_accuracy_score": 0-10,
  "group_validity_score": 0-10,
  "relevance_score_validity": 0-10,
  "context_accuracy_score": 0-10,
  "sport_implication_score": 0-10,
  "overall_alignment": "<excellent|good|acceptable|poor|hallucinated>"
}

Score definitions (short):
- factual_accuracy_score: correctness of all stated effects.
- coverage_score: how fully the summary reflects the paper set.
- hallucination_score: absence of invented content (10 = none).
- direction_accuracy_score: correctness of increase/decrease.
- group_validity_score: correctness of biomarker group assignment.
- relevance_score_validity: is the 1–10 score justified?
- context_accuracy_score: correctness of study setting & conditions.
- sport_implication_score: correctness and non-overstatement of implications.

