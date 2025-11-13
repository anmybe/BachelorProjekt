{
  "title": "Molecular Pathways Mediating Immunosuppression in Response to Prolonged Intensive Physical Training, Low-Energy Availability, and Intensive Weight Loss",
  "abstract": {
    "aim": "To assess how energy deprivation ('semi-starvation') and intensive physical training leading to substantial fat mass loss affect the immune system and immunosuppression in previously normal weight individuals, using a high-throughput systems biology approach.",
    "study_design": "42 healthy female physique athletes (age 27.5 ± 4.0 years, BMI 23.4 ± 1.7 kg/m²) were divided into a diet group (n=25) and a control group (n=17). The diet group reduced energy intake and increased exercise to induce fat mass loss, followed by a weight regain period. Fasting blood samples were drawn at three time points: baseline (PRE), end of the weight loss period (MID) (21.1 ± 3.1 weeks after PRE), and end of the weight regain period (POST) (18.4 ± 2.9 weeks after MID).",
    "main_findings": "In contrast to the control group, the diet group showed significant (false discovery rate <0.05) alteration of all measured immune function parameters—white blood cells (WBCs), immunoglobulin G (IgG) glycome, leukocyte transcriptome, and cytokine profile. Integrative omics suggested effects on multiple levels of immune system after intense weight loss: dysregulated hematopoiesis, suppressed immune cell proliferation, attenuated systemic inflammation, and loss of immune cell function by reduced antibody and chemokine secretion.",
    "recovery": "During the weight regain period, the majority of the measured immune system parameters returned back to the baseline.",
    "conclusion": "This study elucidated molecular pathways presumably explaining immunosuppression in individuals going through prolonged periods of intense training with low-energy availability. Our findings reinforce the perception that the way in which weight loss is achieved (i.e., dietary restriction, exercise, or both) has a distinct effect on how the immune system is modulated."
  },
  "methods": {
    "study_participants_and_design": {
      "recruitment": "Young, previously normal-weight female amateur physique athletes of Caucasian origin (Age 27.5 ± 4.0 years, BMI 23.4 ± 1.7 kg/m²).",
      "groups": "Diet group (n=25) and Control group (n=17) for bioinformatic analysis after exclusions.",
      "exclusion_criteria": "Prevalent diagnosed chronic disease, prescribed medication (excluding contraception), and <2 years of resistance training experience. 18 participants were excluded for various reasons (e.g., failed to complete the regimen, lacked complete dietary records).",
      "protocol": "Diet group followed a progressive competition diet (PRE-MID) and a subsequent weight regain period (MID-POST). Control group maintained their typical lifestyle."
    },
    "measurements": {
      "anthropometrics": "Body composition assessed with Dual-Energy X-ray Absorptiometry (DEXA).",
      "nutrient_intake": "Self-reported dietary diaries analyzed with Aivodiet software.",
      "physical_activity": "Overall physical activity (METh/wk) calculated from reported duration and intensity.",
      "blood_sampling": "Fasting venous blood samples taken from the antecubital vein at PRE, MID, and POST time points."
    },
    "analysis": {
      "wbc_differential_count": "Total and differential WBCs (neutrophils, lymphocytes, mixed cells) measured with Sysmex KX-21N.",
      "glycome_analysis": "IgG isolation from plasma, N-glycans released and labeled with 2-AB, separation by Ultra-Performance Liquid Chromatography (UPLC) to quantify 24 peaks.",
      "cytokine_quantification": "Serum concentrations of 38 markers (chemokines, cytokines, growth factors) analyzed using Multiplexed Luminex Analyses (Milliplex MAP Kit).",
      "transcriptome": "RNA-Sequencing in peripheral leukocytes (Illumina HiSeq2000). Differential expression analysis using DESeq2.",
      "statistical_analysis": "Generalized Estimating Equations (GEEs) for WBC, Glycome, and Cytokines. False Discovery Rate (FDR) applied for multiple testing (FDR < 0.05) for Glycome and Cytokine variables. Likelihood Ratio Test and Wald tests with DESeq2 for the transcriptome (q-value of 0.05 for FDR)."
    }
  },
  "results": {
    "body_composition": {
      "weight_loss_pre_mid": "Significant reduction in body weight (~13%) and total body fat mass (~51%) in the Diet group, achieved by decreased energy intake (~18%) and increased exercise (~15%), resulting in decreased energy availability (~29%).",
      "weight_regain_mid_post": "Most anthropometric changes reverted back to baseline levels."
    },
    "hematopoiesis_and_wbc": {
      "wbc_changes": "Significant increase in absolute numbers of **Neutrophils** and **Total WBC count** (PRE–MID). Relative decrease in the percentage of lymphocytes.",
      "other_blood_cells": "Reduction in **erythrocyte** and **platelet counts**.",
      "transcriptome_findings": "Supported by differential expression of key transcription factors (e.g., $\text{TAL}1, \text{RUNX}1, \text{SPI}1, \text{GATA}1$). Increased $\text{SPI}1$ (PU.1) and reduced $\text{GATA}1$ suggested **suppressed differentiation in erythroid lineage** and **induced activity of myeloid and lymphoid progenitor cell lines**. Downregulation of $\text{FOXO}$ transcription factors implied **increased metabolic stress** (ROS) on hematopoietic stem cells (HSCs)."
    },
    "adaptive_immunity": {
      "t_lymphocytes": "Distinct **downregulation of the adaptive immunity pathway**. Suggested inhibition of T-helper ($\text{T}_{\text{H}}$)/CD4 and cytotoxic/CD8 lymphocyte proliferation (e.g., $\text{GATA}3, \text{RUNX}3, \text{GZMB}$). Findings implied **suppression of the $\text{T}_{\text{H}}1$ cell line** concomitant with a **predominant $\text{T}_{\text{H}}2$ response** (supported by increased $\text{Eotaxin}$ levels).",
      "b_lymphocytes": "**Suppressed B-lymphocyte proliferation** indicated by upregulation of inhibitory BCR signaling genes (e.g., $\text{CD}22, \text{FCGR}2\text{B}$). Reduced maturation to plasma cells implied by upregulation of $\text{BCL}-6$ and downregulation of $\text{BLIMP}$ and $\text{XBP}1$.",
      "igg_antibodies": "**Significant reduction in total isolated $\text{IgG}$ levels** ($\text{FDR} = 4.85 \times 10^{-3}$). **IgG Glycosylation alteration** (PRE–MID): Shift toward **pro-inflammatory activity** (galactosylation $\downarrow$, bisecting $\text{GlcNAc} \uparrow$) and **reduced IgG affinity** (sialylation $\downarrow$)."
    },
    "innate_immunity_and_cytokines": {
      "innate_immunity": "Downregulation of the **innate immunity pathway** in transcriptomics.",
      "cytokine_profile": "Significant reduction in **Tumor Necrosis Factor alpha ($\text{TNF}-\alpha$)** and **Interferon-gamma induced protein 10 ($\text{IP}10$)** (PRE–MID), suggesting **suppressed release of pro-inflammatory chemokines**. $\text{TNF}-\alpha$ levels decreased even further during the weight regain period ($\text{POST}$).",
      "chemotaxis": "Evidence of higher circulating levels of $\text{MCP}1$, $\text{MDC}$, and $\text{GRO}$ (chemokines mediating myeloid cell line proliferation and chemotaxis)."
    }
  },
  "discussion": {
    "immunosuppression_and_wbc": "Augmented neutrophil numbers are observed after the diet, contrasting with previous anorexia nervosa findings. Integrated omics suggest **leukocyte-skewed augmentation in $\text{HSC}$ proliferation** from bone marrow, potentially accelerated by high training volume and energy restriction.",
    "mechanisms_of_suppression": "Immune defects (reduced $\text{T}$-lymphocyte maturation, $\text{CD}4/\text{CD}8$ imbalance, $\text{T}_{\text{H}}2$ response) are typical of malnutrition and are likely mediated by **reduced Leptin levels** observed in the diet group. Normalization of Leptin during weight regain was accompanied by normalization of $\text{T}$-lymphocyte regulatory genes.",
    "b_lymphocyte_and_autoimmunity": "Similar to $\text{T}$-cells, $\text{B}$-lymphocyte proliferation was suppressed, with skewing towards germinal center expansion and diminished mature $\text{IgG}$ production. The observed shifts in $\text{IgG}$ glycosylation (pro-inflammatory $\text{IgG}$, reduced affinity), $\text{IgE}$-signaling alterations, and $\text{T}_{\text{H}}2$ response have been associated with **autoimmune diseases** related to the lungs and intestines. This raises the question of whether these alterations predispose individuals to a greater risk of autoimmune dysregulation.",
    "conclusion_reiteration": "Prolonged periods of low-energy availability and high exercise amount significantly affect multiple levels of the immune system, with most changes being reversible upon sufficient recovery. The findings reinforce that the manner of weight loss (dietary restriction, exercise, or both) distinctly modulates the immune system."
  }
}