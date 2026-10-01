# Medicore Machine Learning Architecture & Clinical Decision-Support Documentation

## 1. Overview & Clinical Safety Disclaimer

> **IMPORTANT MEDICAL NOTICE**
> The machine learning functionality provided within the Medicore platform is strictly a **computational decision-support tool** intended to assist qualified medical practitioners. 
> - **It does NOT provide a medical diagnosis.**
> - **It does NOT establish definitive clinical pathology.**
> - **It does NOT replace professional clinical judgment, physical examination, laboratory investigations, or imaging.**
> - All outputs are classified as **"Preliminary Decision-Support Predictions"** based solely on statistical associations in the training dataset.
> - No autonomous prescriptions or treatments are initiated by the ML pipeline.

---

## 2. Model Specification & Architecture

| Parameter | Specification |
| :--- | :--- |
| **Model Type** | Multinomial Naive Bayes (`sklearn.naive_bayes.MultinomialNB`) |
| **Artifact File** | `BASE_DIR / 'trained_model'` (Binary Joblib serialization) |
| **Dimensionality** | 132 binary input features ($\mathbf{x} \in \{0, 1\}^{132}$) |
| **Output Classes** | 41 disease categories |
| **Confidence Scoring** | Direct posterior class probability vector via `predict_proba()` |
| **Inference Mode** | Thread-safe in-memory singleton cache with dynamic warm-up |
| **Dataset Source** | Kaggle Disease Symptom Prediction dataset (Academic/Educational) |

### Algorithmic Foundation
The model applies Bayes' theorem with the Naive Bayes feature independence assumption:

$$P(Y = c_k \mid \mathbf{x}) = \frac{P(Y = c_k) \prod_{i=1}^{132} P(X_i = x_i \mid Y = c_k)}{\sum_{j=1}^{41} P(Y = c_j) \prod_{i=1}^{132} P(X_i = x_i \mid Y = c_j)}$$

Where:
- $c_k$ represents disease class $k$ among 41 possible conditions.
- $\mathbf{x} = [x_1, x_2, \dots, x_{132}]$ is the binary indicator vector of patient symptoms.
- Prior probabilities $P(Y = c_k)$ are derived from class frequencies in the training distribution.
- Posterior probabilities are computed directly through Scikit-Learn's `predict_proba` method. **Confidence values are NEVER manufactured or fabricated.**

---

## 3. Feature Ordering & Index Mapping

The pre-trained model expects an exact 132-element input vector. Any reordering or omission shifts the input into incorrect categorical features. The authoritative feature indices are preserved in `Doctor/ml_service.py`:

```python
FEATURE_SYMPTOMS = [
    'itching', 'skin_rash', 'nodal_skin_eruptions', 'continuous_sneezing', 'shivering',
    'chills', 'joint_pain', 'stomach_pain', 'acidity', 'ulcers_on_tongue',
    'muscle_wasting', 'vomiting', 'burning_micturition', 'spotting_ urination', 'fatigue',
    'weight_gain', 'anxiety', 'cold_hands_and_feets', 'mood_swings', 'weight_loss',
    'restlessness', 'lethargy', 'patches_in_throat', 'irregular_sugar_level', 'cough',
    'high_fever', 'sunken_eyes', 'breathlessness', 'sweating', 'dehydration',
    'indigestion', 'headache', 'yellowish_skin', 'dark_urine', 'nausea',
    'loss_of_appetite', 'pain_behind_the_eyes', 'back_pain', 'constipation', 'abdominal_pain',
    'diarrhoea', 'mild_fever', 'yellow_urine', 'yellowing_of_eyes', 'acute_liver_failure',
    'fluid_overload', 'swelling_of_stomach', 'swelled_lymph_nodes', 'malaise', 'blurred_and_distorted_vision',
    'phlegm', 'throat_irritation', 'redness_of_eyes', 'sinus_pressure', 'runny_nose',
    'congestion', 'chest_pain', 'weakness_in_limbs', 'fast_heart_rate', 'pain_during_bowel_movements',
    'pain_in_anal_region', 'bloody_stool', 'irritation_in_anus', 'neck_pain', 'dizziness',
    'cramps', 'bruising', 'obesity', 'swollen_legs', 'swollen_blood_vessels',
    'puffy_face_and_eyes', 'enlarged_thyroid', 'brittle_nails', 'swollen_extremeties', 'excessive_hunger',
    'extra_marital_contacts', 'drying_and_tingling_lips', 'slurred_speech', 'knee_pain', 'hip_joint_pain',
    'muscle_weakness', 'stiff_neck', 'swelling_joints', 'movement_stiffness', 'spinning_movements',
    'loss_of_balance', 'unsteadiness', 'weakness_of_one_body_side', 'loss_of_smell', 'bladder_discomfort',
    'foul_smell_of urine', 'continuous_feel_of_urine', 'passage_of_gases', 'internal_itching', 'toxic_look_(typhos)',
    'depression', 'irritability', 'muscle_pain', 'altered_sensorium', 'red_spots_over_body',
    'belly_pain', 'abnormal_menstruation', 'dischromic _patches', 'watering_from_eyes', 'increased_appetite',
    'polyuria', 'family_history', 'mucoid_sputum', 'rusty_sputum', 'lack_of_concentration',
    'visual_disturbances', 'receiving_blood_transfusion', 'receiving_unsterile_injections', 'coma', 'stomach_bleeding',
    'distention_of_abdomen', 'history_of_alcohol_consumption', 'fluid_overload', 'blood_in_sputum', 'prominent_veins_on_calf',
    'palpitations', 'painful_walking', 'pus_filled_pimples', 'blackheads', 'scurring',
    'skin_peeling', 'silver_like_dusting', 'small_dents_in_nails', 'inflammatory_nails', 'blister',
    'red_sore_around_nose', 'yellow_crust_ooze'
]
```

### Dataset Anomaly Resolution: `fluid_overload`
- In the original Kaggle dataset, the feature label `fluid_overload` appears twice: at index 45 and index 117.
- Analysis shows index 45 was an unweighted column (zero frequency across classes), while index 117 contains class weight for Alcoholic Hepatitis.
- `Doctor/ml_service.py` handles this anomaly through an index-list mapping: when `fluid_overload` is selected, **both** indices [45, 117] are activated in the feature vector, guaranteeing full mathematical compatibility with the pre-trained weights.

---

## 4. Input Normalization & Canonical Mapping

Raw clinical inputs, dataset artifacts, or variations in whitespace/formatting are normalized through canonical aliases without altering model semantics:

| Raw Input Variation | Canonical Feature Name |
| :--- | :--- |
| `spotting_ urination` / `spotting urination` | `spotting_ urination` (Index 13) |
| `cold_hands_and_feets` / `cold hands and feet` | `cold_hands_and_feets` (Index 17) |
| `foul_smell_of urine` / `foul smell of urine` | `foul_smell_of urine` (Index 90) |
| `toxic_look_(typhos)` / `toxic look (typhos)` | `toxic_look_(typhos)` (Index 94) |
| `dischromic _patches` / `dischromic patches` | `dischromic _patches` (Index 102) |

---

## 5. Clinical Body System Grouping

For optimal clinical usability, the 131 unique symptoms are categorized into 7 physiological domains:

1. **Skin & Dermatology**: `skin_rash`, `itching`, `blister`, `nodal_skin_eruptions`, `pus_filled_pimples`, etc.
2. **Respiratory & ENT**: `cough`, `breathlessness`, `continuous_sneezing`, `sinus_pressure`, `blood_in_sputum`, etc.
3. **Gastrointestinal & Hepatic**: `vomiting`, `abdominal_pain`, `acidity`, `nausea`, `yellowish_skin`, `stomach_bleeding`, etc.
4. **Neurological & Sensory**: `headache`, `dizziness`, `altered_sensorium`, `loss_of_balance`, `slurred_speech`, etc.
5. **Musculoskeletal**: `joint_pain`, `back_pain`, `muscle_weakness`, `stiff_neck`, `knee_pain`, etc.
6. **Urinary & Reproductive**: `burning_micturition`, `bladder_discomfort`, `polyuria`, `abnormal_menstruation`, etc.
7. **Systemic & General**: `fatigue`, `high_fever`, `chills`, `malaise`, `weight_loss`, `anxiety`, etc.

---

## 6. End-to-End Prediction Pipeline

```
           User / Doctor Selection
                      │
                      ▼
     ┌──────────────────────────────────┐
     │ 1. Input Validation              │  Empty check, max-bound check (<= 25),
     │    & Normalization               │  canonical alias resolution, duplicate elimination
     └────────────────┬─────────────────┘
                      │
                      ▼
     ┌──────────────────────────────────┐
     │ 2. Feature Vector Construction   │  132-dimension binary numpy array
     │    (Exact Model Order)           │  x[i] in {0, 1}
     └────────────────┬─────────────────┘
                      │
                      ▼
     ┌──────────────────────────────────┐
     │ 3. Model Inference               │  Thread-safe singleton MultinomialNB
     │    (Joblib Cached Instance)      │  predict() & predict_proba()
     └────────────────┬─────────────────┘
                      │
                      ▼
     ┌──────────────────────────────────┐
     │ 4. Differential Analysis         │  Extract Top-3 candidates with genuine
     │    & Probability Sorting         │  posterior probabilities
     └────────────────┬─────────────────┘
                      │
                      ▼
     ┌──────────────────────────────────┐
     │ 5. Clinical Decision Output      │  Saved to tbl_disease with confidence score
     │    & Medical Disclaimer          │  Rendered with decision-support disclaimers
     └──────────────────────────────────┘
```

### Input Validation Guards:
- **Empty Selection**: Submitting empty symptom lists is intercepted immediately (`MLValidationError`), rejecting the query before execution. (In previous revisions, an empty vector erroneously predicted `Hypoglycemia` at 2.9%).
- **Maximum Symptom Bound**: Capped at 25 symptoms to prevent denial-of-service or malformed payload abuse.
- **Whitelist Enforcement**: Only symptoms present in the 132-feature definition are accepted. Arbitrary feature names are rejected.
- **Duplicate Prevention**: Symptoms are deduplicated during normalization.

---

## 7. Model Loading & Thread Safety

- **Loading Strategy**: Model is loaded via `Doctor/ml_service.py` using `pathlib.Path(settings.BASE_DIR) / 'trained_model'`.
- **Absolute Path Resolution**: No reliance on `os.getcwd()` or process working directory.
- **Thread-Safe Caching**: Utilizes Python's `threading.Lock` to guarantee atomic initialization without race conditions under multi-threaded WSGI/ASGI deployments.
- **Graceful Error Handling**: If the model artifact is missing or corrupt, an `MLServiceError` is logged internally, and a clean user-facing error message is returned without leaking server paths or tracebacks.

---

## 8. Privacy & Data Protection

1. **Role-Based Isolation**:
   - Only verified, authenticated medical practitioners (`role == 'doctor'`) can trigger clinical symptom assessments for patient consultation requests.
   - Patients can only view predictions and consultations tied to their own authenticated user ID.
2. **Audit & Traceability**:
   - Disease predictions are permanently recorded in `tbl_disease` with the associated consultation request, the selected symptoms, the predicted condition, the model's confidence score, and the timestamp.
3. **No Direct PHI in URLs**: All evaluation actions occur via POST with CSRF tokens.

---

## 9. Dependency Requirements

- `Django>=5.1.0,<6.2.0`
- `scikit-learn>=1.6.0`
- `joblib>=1.4.0`
- `numpy>=2.0.0`
- `scipy>=1.14.0`

---

## 10. Technical Limitations & Future Work

1. **Small Educational Dataset**: The model was trained on a synthetic, discrete symptom-disease matrix from Kaggle. It reflects academic benchmark patterns rather than real-world epidemiology.
2. **Binary Symptom Indicators**: The model only considers symptom presence (1) or absence (0). It does not take into account symptom severity, duration, patient age, gender, vital signs, or lab values.
3. **Independent Feature Assumption**: Naive Bayes assumes symptoms occur independently given the disease, which does not hold true in complex human pathophysiology.
4. **Conclusion**: This model serves strictly as an educational and workflow demonstration for the Medicore platform and must not be utilized for real-world medical diagnosis.
