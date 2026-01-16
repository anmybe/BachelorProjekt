# Biomarker Uncovered: Rise of the Athlete 🏃‍♂️🔬

### KI-gestützte Analyse von Metadaten in der personalisierten Medizin

Dieses Projekt wurde im Rahmen eines Bachelorprojekts in Zusammenarbeit mit der **RICB Diagnostics AG** entwickelt. Es bietet ein System zur automatisierten Extraktion und Analyse von Biomarkern aus wissenschaftlicher Literatur, um komplexe Studienergebnisse in direkt anwendbare Trainingserkenntnisse zu übersetzen.

## 📖 Hintergrund & Problemstellung

Wissenschaftliche Erkenntnisse über Biomarker sind oft über tausende Studien verstreut, schwer lesbar und lassen sich nur mühsam in die tägliche Trainingspraxis übertragen. Trainer haben kaum Zugang zu diesen Daten, obwohl Training ständig körperliche Veränderungen wie Müdigkeit oder Entzündungen auslöst. Unser System schliesst diese Lücke, indem es messbare Signale des Körpers für Gesundheit, Belastung und Leistung systematisch auswertet.

## 🛠 Die Pipeline

Das Herzstück des Projekts ist eine mehrstufige Verarbeitungs-Pipeline:

1.  **Stage 1 & 2: Paper Erfassung & Segmentierung:** Identifikation relevanter Studien via PubMed und Aufbereitung des Textes in logische Abschnitte (Chunking).
2.  **Stage 3: Analyse pro Paper (`stage3.py`):** Ein LLM extrahiert Biomarker, Kontexte und Effekte aus den Chunks in ein strenges **JSON-Format**. Die Ergebnisse werden in `stage3/stage3_Results/` gespeichert.
3.  **Stage 4: Aggregation & Standardisierung:** Zusammenführung der Daten über alle Dokumente hinweg:
    - **Stage 4.1 (`stage4-1.py`):** Regelbasierte Vorab-Standardisierung und Clusterung ähnlicher Namen (Output: `biomarker-name-list(4-1).json`).
    - **Stage 4.2 (`stage4-2.py`):** KI-gestützte semantische Standardisierung zur Erkennung von Synonymen (Output: `biomarker-list-standardized(4-2).json`).
    - **Stage 4.3 (`stage4-3.py`):** Finale Aggregation aller Details unter den standardisierten Namen (Output: `consolidated-list(4-3).json`).
4.  **Stage 5: Bewertung (`stage5.py`):** Finale Einordnung der Biomarker hinsichtlich ihrer Relevanz für Training, Leistung und Regeneration (Output: CSV).

## 💻 Technische Details: Aggregation & Standardisierung (Stage 4)

Die Aggregation der Daten erfolgt in drei präzisen Teilschritten, um Konsistenz über ca. 5'000 verarbeitete Dokumente hinweg zu gewährleisten:

### Stage 4.1: Regelbasierte Vorab-Standardisierung (Python)

Grobe Clusterung von ähnlichen Namen mittels statischem Mapping (z.B. Mapping von "CD72" auf "Cluster of Differentiation 72"). Dies bereitet die Daten optimal für den KI-Einsatz vor.

### Stage 4.2: Semantische Standardisierung & Chunking (KI-gestützt)

- **Sortierung:** Die Liste wird vorab nach dem Namen sortiert, damit Synonyme im gleichen Kontext verarbeitet werden.
- **KI-Clustering:** Ein LLM erkennt semantische Synonyme (z.B. "LL-37" und "Cathelicidin") und weist einen autoritativen `standard_name` zu.
- **Parallelisierung:** Die Daten werden in Batches (z.B. 150 Einträge) aufgeteilt und mittels `ThreadPoolExecutor` parallel verarbeitet, um die API-Laufzeit zu optimieren.

### Stage 4.3: Finale Detail-Aggregation (Python)

Zusammenführung aller extrahierten Original-Details (Effekte, Mechanismen) aus den Initial-Analysen unter dem neuen Standardnamen in eine konsolidierte Datenbank.

## 🚀 Herausforderungen & Learnings

- **LLM Prompting:** Entwicklung extrem langer Prompts, um sicherzustellen, dass die KI keine Daten erfindet und den Output exakt im JSON-Format liefert.
- **Skalierbarkeit:** Anpassung der Architektur, um das hohe Paper-Volumen ohne Überschreitung von Kontext-Limits zu bewältigen.
- **Modell-Auswahl:** Abwägung zwischen Kosten und Qualität; Wechsel von lokalen Modellen (Ollama) zu leistungsfähigen Cloud-Modellen aufgrund der Ergebnisqualität.

## 👥 Autoren

- **An My Behrendt**
- **Mia Baudri**

---

_Hinweis: Dieses Projekt entstand in Kooperation mit der RICB Diagnostics AG_
