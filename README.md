# Biomarker Uncovered: Rise of the Athlete 🏃‍♂️🔬

### AI-supported Analysis of Metadata in Personalized Medicine

This project was developed as part of a bachelor's project in collaboration with **RICB Diagnostics AG**. It provides a system for the automated extraction and analysis of biomarkers from scientific literature to translate complex study results into directly applicable training insights.

## 📖 Background & Problem Statement

Scientific findings on biomarkers are often scattered across thousands of studies, difficult to read, and laborious to apply to daily training practice. Coaches have little access to this data, even though training constantly triggers physical changes like fatigue or inflammation. Our system bridges this gap by systematically evaluating measurable body signals for health, load, and performance.

## 🛠 The Pipeline

The core of the project is a multi-stage processing pipeline:

1.  **Stage 1 & 2: Paper Collection & Segmentation:** Identification of relevant studies via PubMed and preparation of the text into logical sections (chunking).
2.  **Stage 3: Analysis per Paper (`stage3.py`):** An LLM extracts biomarkers, contexts, and effects from the chunks into a strict **JSON format**. Results are saved in `stage3/stage3_Results/`.
3.  **Stage 4: Aggregation & Standardization:** Merging data across all documents:
    - **Stage 4.1 (`stage4-1.py`):** Rule-based pre-standardization and clustering of similar names (Output: `biomarker-name-list(4-1).json`).
    - **Stage 4.2 (`stage4-2.py`):** AI-supported semantic standardization to detect synonyms (Output: `biomarker-list-standardized(4-2).json`).
    - **Stage 4.3 (`stage4-3.py`):** Final aggregation of all details under the standardized names (Output: `consolidated-list(4-3).json`).
4.  **Stage 5: Evaluation (`stage5.py`):** Final classification of biomarkers regarding their relevance for training, performance, and recovery (Output: CSV).

## 🚀 Challenges & Learnings

- **LLM Prompting:** Development of extremely long prompts to ensure the AI does not hallucinate data and delivers output exactly in JSON format.
- **Scalability:** Adaptation of the architecture to handle the high volume of papers without exceeding context limits.
- **Model Selection:** Balancing cost and quality; switching from local models (Ollama) to powerful cloud models due to result quality.

## 👥 Authors

- **An My Behrendt**
- **Mia Baudri**

---

_Note: This project was developed in cooperation with RICB Diagnostics AG_
