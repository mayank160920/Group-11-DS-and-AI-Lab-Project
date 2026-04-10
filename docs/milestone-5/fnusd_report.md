## FUNSD Evaluation

To assess validation performance, we evaluate the system under two complementary classification settings. This dual evaluation helps separate **high-level decision reliability** from **fine-grained semantic understanding**.

---

### Evaluation Setup

* **Verdict (Derived Label):**
  A normalized, application-level decision used in downstream workflows:

  * `match`: Indicates agreement between compared fields
    (includes both exact and semantic matches)
  * `conflict`: Indicates disagreement or inconsistency

* **Category (Fine-Grained Label):**
  A more detailed classification used for deeper analysis:

  * `exact_match`: Identical values
  * `semantic_match`: Equivalent meaning but different representation
  * `conflict`: Disagreement

---

### Why Two Evaluation Settings?

* **2-Class (Verdict-based):**

  * Reflects the **actual production use-case**, where the system must decide whether two fields agree or not.
  * Prioritizes **decision accuracy and reliability**.

* **3-Class (Category-based):**

  * Evaluates the model’s ability to **distinguish nuanced agreement types**.
  * Helps diagnose **failure modes and boundary confusion** (e.g., exact vs semantic).

---

## Examples

### 2-Class (Verdict: Match vs. Conflict)

This setting collapses fine-grained distinctions into a binary decision.

| Field A          | Field B          | Category       | Verdict  |
| ---------------- | ---------------- | -------------- | -------- |
| "Invoice #12345" | "Invoice #12345" | exact_match    | match    |
| "01/02/2024"     | "1 Feb 2024"     | semantic_match | match    |
| "$100.00"        | "$100"           | semantic_match | match    |
| "Total: $100"    | "Total: $120"    | conflict       | conflict |

**Interpretation:**
* Even though representations may differ (formatting, wording), as long as the meaning aligns, the system should output **`match`**.

---

### 3-Class (Category: Exact vs. Semantic vs. Conflict)

This setting requires finer distinctions between types of agreement.

| Field A               | Field B              | Category       |
| --------------------- | -------------------- | -------------- |
| "ABC Ltd."            | "ABC Ltd."           | exact_match    |
| "Jan 1, 2024"         | "01/01/2024"         | semantic_match |
| "One hundred dollars" | "$100"               | semantic_match |
| "Invoice Total: 500"  | "Invoice Total: 700" | conflict       |

**Interpretation:**

* `exact_match` → identical strings
* `semantic_match` → same meaning, different surface form
* `conflict` → actual disagreement

---

## 2-Class Evaluation (Verdict: Match vs. Conflict)

| Metric                   |  Value |
| ------------------------ | -----: |
| Samples Evaluated        |    279 |
| Accuracy                 | 0.8853 |
| Precision (Weighted Avg) |   0.91 |
| Recall (Weighted Avg)    |   0.89 |
| F1 Score (Weighted Avg)  |   0.89 |

### Class-wise Performance

| Class    | Precision | Recall | F1 Score | Support |
| -------- | --------: | -----: | -------: | ------: |
| conflict |      0.56 |   0.79 |     0.66 |      39 |
| match    |      0.96 |   0.90 |     0.93 |     240 |

### Observations

* Strong performance at the **verdict level (88.53% accuracy)** confirms reliability for real-world validation decisions.
* **Match predictions are highly accurate**, with strong precision and recall.
* **Conflict detection shows lower precision**, indicating some over-flagging of disagreements.
* Error distribution suggests a **conservative validation bias**, favoring conflict when uncertain.

---

## 3-Class Evaluation (Category: Exact vs. Semantic vs. Conflict)

| Metric                   |  Value |
| ------------------------ | -----: |
| Accuracy                 | 0.7168 |
| Precision (Weighted Avg) |   0.75 |
| Recall (Weighted Avg)    |   0.72 |
| F1 Score (Weighted Avg)  |   0.71 |

### Class-wise Performance

| Class          | Precision | Recall | F1 Score | Support |
| -------------- | --------: | -----: | -------: | ------: |
| conflict       |      0.56 |   0.79 |     0.66 |      39 |
| exact_match    |      0.88 |   0.56 |     0.68 |     118 |
| semantic_match |      0.69 |   0.84 |     0.76 |     122 |

### Observations

* Performance drops under stricter classification (**71.68% accuracy**), reflecting the difficulty of fine-grained distinctions.
* **Semantic matches are well captured (high recall)**, but often absorb exact matches.
* **Exact matches are under-detected (low recall)** despite high precision.
* The dominant error mode is **confusion between exact and semantic matches**, not conflict detection.
* Conflict detection remains **stable and consistent across both setups**.

---

## Summary

* The system is **reliable for production-level validation decisions** (match vs. conflict).
* Performance degradation in the 3-class setting is driven by **boundary ambiguity between exact and semantic equivalence**, not by failure in detecting disagreement.
* The model exhibits:

  * **Conservative behavior for exact matches** (high precision, low recall)
  * **Generalization bias toward semantic matches** (high recall)
* Overall, the pipeline is well-suited for **coarse validation tasks**, with clear opportunities to improve **fine-grained equivalence calibration**.
