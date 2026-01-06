# Biomarker Uncovered: Rise of the Athlete 🏃‍♂️🔬

### KI-gestützte Analyse von Metadaten in der personalisierten Medizin

Dieses Projekt wurde im Rahmen eines Bachelorprojekts in Zusammenarbeit mit der **RICB Diagnostics AG** entwickelt. Es bietet ein System zur automatisierten Extraktion und Analyse von Biomarkern aus wissenschaftlicher Literatur, um komplexe Studienergebnisse in direkt anwendbare Trainingserkenntnisse zu übersetzen.

## 📖 Hintergrund & Problemstellung
Wissenschaftliche Erkenntnisse über Biomarker sind oft über tausende Studien verstreut, schwer lesbar und lassen sich nur mühsam in die tägliche Trainingspraxis übertragen. Trainer haben kaum Zugang zu diesen Daten, obwohl Training ständig körperliche Veränderungen wie Müdigkeit oder Entzündungen auslöst. Unser System schliesst diese Lücke, indem es messbare Signale des Körpers für Gesundheit, Belastung und Leistung systematisch auswertet.

## 🛠 Die Pipeline
Das Herzstück des Projekts ist eine fünfstufige Verarbeitungs-Pipeline:

1.  **Paper Erfassung:** Identifikation relevanter Studien via PubMed und Übernahme als strukturierter Text.
2.  **Segmentierung:** Aufbereitung des Textes durch ein KI-Modell in logische, verarbeitbare Abschnitte.
3.  **Analyse pro Paper:** Ein LLM extrahiert Biomarker, Kontexte und Effekte in ein strenges **JSON-Format**.
4.  **Aggregation:** Zusammenführung der Daten über alle Dokumente hinweg (siehe "Technische Details").
5.  **Bewertung:** Einordnung der Biomarker hinsichtlich ihrer Relevanz für Training, Leistung und Regeneration.

## 💻 Technische Details: Aggregation & Standardisierung
Die Aggregation der Daten erfolgt in drei präzisen Teilschritten, um Konsistenz über ca. 5'000 verarbeitete Dokumente hinweg zu gewährleisten:

### Schritt 1: Regelbasierte Vorab-Standardisierung (Python)
Grobe Clusterung von ähnlichen Namen mittels statischem Mapping (z.B. Mapping von "CD72" auf "Cluster of Differentiation 72"). Dies bereitet die Daten optimal für den KI-Einsatz vor.

### Schritt 2: Semantische Standardisierung & Chunking (KI-gestützt)
* **Sortierung:** Die Liste wird vorab nach dem Namen sortiert, damit Synonyme im gleichen Kontext verarbeitet werden.
* **KI-Clustering:** Ein LLM erkennt semantische Synonyme (z.B. "LL-37" und "Cathelicidin") und weist einen autoritativen `standard_name` zu.
* **Parallelisierung:** Die Daten werden in Batches (z.B. 150 Einträge) aufgeteilt und mittels `ThreadPoolExecutor` parallel verarbeitet, um die API-Laufzeit zu optimieren.

### Schritt 3: Finale Detail-Aggregation (Python)
Zusammenführung aller extrahierten Original-Details (Effekte, Mechanismen) aus den Initial-Analysen unter dem neuen Standardnamen in eine konsolidierte Datenbank.

## 🚀 Herausforderungen & Learnings
* **LLM Prompting:** Entwicklung extrem langer Prompts, um sicherzustellen, dass die KI keine Daten erfindet und den Output exakt im JSON-Format liefert.
* **Skalierbarkeit:** Anpassung der Architektur, um das hohe Paper-Volumen ohne Überschreitung von Kontext-Limits zu bewältigen.
* **Modell-Auswahl:** Abwägung zwischen Kosten und Qualität; Wechsel von lokalen Modellen (Ollama) zu leistungsfähigen Cloud-Modellen aufgrund der Ergebnisqualität.

## 👥 Autoren
* **An My Behrendt**
* **Mia Baudri**

---
*Hinweis: Dieses Projekt entstand in Kooperation mit der RICB Diagnostics AG und dem rict.*