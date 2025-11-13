{
  "title": "Effects of Different Doses of Exercise on Inflammation Markers Among Adolescents With Overweight/Obesity: HEPAFIT Study",
  "abstract": {
    "propose": "To investigate whether 6 months of exercise training altered markers of inflammation in adolescents who are overweight/obese, where obesity-related metabolic risk factors may be associated with systemic low-grade inflammation.",
    "methods": "Secondary analyses of a randomized controlled exercise-based intervention trial (HEPAFIT Study). Adolescents (11 to 17 years) with BMI z-score at or above the 85th percentile and/or excess adiposity ($\ge 30\%$ body fat) were randomly assigned to 4 groups for 6 months: (1) Control (CTRL, standard physical education); (2) High-Intensity PE (HIPE); (3) Low-to-Moderate Intensity PE (LIPE); (4) Combined Group (PLUS). Inflammatory markers and immune molecules ($\text{n}=65$ biomarkers) were determined by cytokine antibody array.",
    "results": "Of the 120 randomized participants, 95 completed the study. A subanalysis performed (adjusted P-value $\le 0.05$ and absolute $\text{logFC} \ge 1.0$) showed 3 downregulated proteins in the **LIPE** group ($\text{BLC}, \text{Eotaxin}, \text{MCP}-4$) and 4 proteins in the **HIPE** group ($\text{BLC}, \text{FGF}-6, \text{MCP}-4, \text{PARC}$), supporting that changes occurred in response to exercise, not time-related effects.",
    "conclusions": "Implementing a 6-month physical exercise program in overweight/obese adolescents, based on $\text{LIPE}$ and $\text{PLUS}$ groups, significantly changes several circulating inflammatory levels. Supervised physical exercise may reduce the associated effects of systemic low-grade inflammation, preventing the development of obesity-related metabolic diseases."
  },
  "methods": {
    "study_design": "Secondary analysis of a randomized controlled exercise-based intervention trial (HEPAFIT Study).",
    "participants": {
      "criteria": "Adolescents (11 to 17 years), Tanner stage II–V, with overweight/obese status (BMI z-score $\ge 85$th percentile and/or body fat $\ge 30\%$). 70% were girls.",
      "exclusions": "Habitual exercise more than twice weekly, pregnancy, cardiovascular disease, diabetes mellitus, or other debilitating illness. Other causes of liver disease were excluded."
    },
    "intervention": {
      "protocol": "6 months of school-based exercise programs, 3 times weekly. No caloric restriction.",
      "groups": "CTRL (Control); HIPE (High-Intensity PE); LIPE (Low-to-Moderate Intensity PE); PLUS (Combined $\text{HIPE}$ and $\text{LIPE}$).",
      "monitoring": "Heart rate monitors used to adjust workloads. Compliance defined as successfully completing $\text{>70\%}$ of scheduled sessions at target HR."
    },
    "inflammatory_markers_analysis": {
      "blood_samples": "Venous blood samples obtained following a 10- to 12-hour overnight fast.",
      "quantification": "Quantification of 80 analytes in serum using the Abcam Human Cytokine Antibody Array (80 targets).",
      "data_processing": "Data measured as intensities, background corrected, and normalized. $\text{Log}_2$ transformed data normalized using the quantile algorithm. The $\text{limma}$ $\text{R}$ package used for statistical significance. Significance level adjusted using a $\text{False Discovery Rate (FDR)}$ of $\text{0.1}$."
    }
  },
  "results": {
    "participant_outcomes": "95 participants completed the study (79\%). Baseline characteristics were similar across groups. Mean age $13.5$ years, mean BMI z-score $1.8$, mean body fat $39.9\%$.",
    "body_fat_change": "Body fat decreased significantly in the **HIPE** group ($\text{-2.88\%}$, $\text{P}=0.001$) and the **LIPE** group ($\text{-0.62\%}$, $\text{P}=0.014$), independent of dietary intake.",
    "cytokine_profile_changes": {
      "overall_changes": "The intervention effects differed from baseline in 22/65 proteins (median 33.8\%).",
      "subanalysis_logfc_greater_equal_1_0_downregulated": "\n- **LIPE** (3 proteins): $\text{BLC}(\text{logFC}=1.27)$, $\text{Eotaxin}(\text{logFC}=1.18)$, $\text{MCP}-4(\text{logFC}=1.14)$.\n- **HIPE** (4 proteins): $\text{BLC}(\text{logFC}=1.45)$, $\text{FGF}-6(\text{logFC}=1.20)$, $\text{MCP}-4(\text{logFC}=1.50)$, $\text{PARC}(\text{logFC}=1.33)$.",
      "significant_time_x_group_interaction_vs_ctrl_logfc_greater_than_1_0_decreased": "\n- **LIPE** group: $\text{BLC}(\text{logFC}=1.65)$, $\text{Eotaxin}(\text{logFC}=1.45)$, $\text{FGF}-6(\text{logFC}=1.04)$, $\text{PARC}(\text{logFC}=1.27)$.\n- **PLUS** group: $\text{BLC}(\text{logFC}=1.83)$, $\text{Eotaxin}(\text{logFC}=1.50)$, $\text{FGF}-6(\text{logFC}=1.42)$, $\text{MCP}-4(\text{logFC}=1.73)$, $\text{MIG}(\text{logFC}=1.26)$, $\text{PARC}(\text{logFC}=1.60)$.",
      "common_decrease": "Five interleukins/chemokines ($\text{MIP}-1\text{b}, \text{RANTES}, \text{BLC}, \text{Eotaxin}, \text{PARC}$), in addition to $\text{FGF}-6$, decreased significantly in response to exercise in the $\text{HIPE}$ and $\text{PLUS}$ groups ($\text{P}<0.05$).",
      "functional_relationships": "Fluctuations suggest the response to exercise generally affects chemokine-mediated signaling pathway ($\text{FDR}: 4.31\text{e}-23$), inflammatory response ($\text{FDR}: 2.91\text{e}-17$), and chemotaxis ($\text{FDR}: 1.56\text{e}-15$)."
    }
  },
  "discussion": {
    "main_finding_and_implication": "Both $\text{LIPE}$ and $\text{PLUS}$ groups were associated with significant reductions in several cytokine levels, supporting the anti-inflammatory effect of these programs. This aligns with international recommendations for combined moderate-to-vigorous aerobic activity and resistance training.",
    "key_chemokine_reductions": "Serum levels of $\text{MIP}-1\text{b}, \text{RANTES}, \text{BLC}, \text{Eotaxin}, \text{PARC}$, and $\text{FGF}-6$ decreased significantly in the $\text{LIPE}$ and $\text{PLUS}$ groups.",
    "interpretation_of_reductions": "\n- $\text{MIP}-1\text{b}$ and $\text{RANTES}$ (pro-inflammatory) decrease, hypothesized to be due to **weight loss** accompanying physical training.\n- $\text{BLC}$ ($\text{CXCL}13$) is produced at elevated levels during adipogenesis.\n- $\text{PARC}$ ($\text{CCL}18$) levels are higher in obese patients and correlated with $\text{TNF}-\alpha$ and $\text{IL}-6$.\n- $\text{FGF}-6$ decreased, supporting the anti-inflammatory properties of physical exercise.",
    "mcp_4_as_a_biomarker": "A significant reduction in $\text{MCP}-4$ ($\text{CCL}13$) was observed in all exercise groups. $\text{MCP}-4$ is a critical molecule linking obesity with chronic inflammation and could play an indirect role in favoring subclinical atherosclerosis. Exercise may decrease $\text{MCP}-4$ plasma levels $\text{in vivo}$.",
    "intensity_effect": "The reduction in inflammatory markers in the $\text{LIPE}$ group (low-to-moderate intensity) suggests that increases in light physical activity intensity mimic regular training and can improve subclinical inflammation.",
    "limitations": "Relatively modest sample size, conducted in a school setting (limited generalizability to thin subjects). Blinding was impossible. Unmeasured changes other than diet and physical activity might have contributed to chronic inflammation alleviation."
  }
}