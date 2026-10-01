"""
ML Disease Decision Support Service for Medicore.

Maintains the exact 132-feature vector order required by the pre-trained MultinomialNB model
while providing robust input validation, symptom normalization, clinical body-system
categorization, differential diagnostic suggestions, and medical safety disclaimers.

IMPORTANT CLINICAL SAFETY NOTICE:
Algorithmic predictions provided by this module are intended strictly for clinical
decision-support assistance to licensed medical professionals. They DO NOT constitute a medical
diagnosis or treatment plan and must never replace clinical judgment by a qualified doctor.
"""

import logging
import threading
from pathlib import Path
from django.conf import settings
import joblib

logger = logging.getLogger(__name__)

# Model versioning and metadata
MODEL_VERSION = "1.0.0"
MODEL_TYPE = "MultinomialNB"
MODEL_FEATURE_COUNT = 132
MODEL_CLASSES_COUNT = 41
MAX_SYMPTOM_SELECTION_LIMIT = 25

# EXACT 132-symptom feature order expected by the pre-trained model.
# NOTE: Index 45 and Index 117 are both 'fluid_overload' in the original 132-feature dataset.
RAW_SYMPTOMS = [
    'itching', 'skin_rash', 'nodal_skin_eruptions', 'continuous_sneezing', 'shivering', 'chills',
    'joint_pain', 'stomach_pain', 'acidity', 'ulcers_on_tongue', 'muscle_wasting', 'vomiting',
    'burning_micturition', 'spotting_ urination', 'fatigue', 'weight_gain', 'anxiety',
    'cold_hands_and_feets', 'mood_swings', 'weight_loss', 'restlessness', 'lethargy',
    'patches_in_throat', 'irregular_sugar_level', 'cough', 'high_fever', 'sunken_eyes',
    'breathlessness', 'sweating', 'dehydration', 'indigestion', 'headache', 'yellowish_skin',
    'dark_urine', 'nausea', 'loss_of_appetite', 'pain_behind_the_eyes', 'back_pain',
    'constipation', 'abdominal_pain', 'diarrhoea', 'mild_fever', 'yellow_urine',
    'yellowing_of_eyes', 'acute_liver_failure', 'fluid_overload', 'swelling_of_stomach',
    'swelled_lymph_nodes', 'malaise', 'blurred_and_distorted_vision', 'phlegm',
    'throat_irritation', 'redness_of_eyes', 'sinus_pressure', 'runny_nose', 'congestion',
    'chest_pain', 'weakness_in_limbs', 'fast_heart_rate', 'pain_during_bowel_movements',
    'pain_in_anal_region', 'bloody_stool', 'irritation_in_anus', 'neck_pain', 'dizziness',
    'cramps', 'bruising', 'obesity', 'swollen_legs', 'swollen_blood_vessels',
    'puffy_face_and_eyes', 'enlarged_thyroid', 'brittle_nails', 'swollen_extremeties',
    'excessive_hunger', 'extra_marital_contacts', 'drying_and_tingling_lips',
    'slurred_speech', 'knee_pain', 'hip_joint_pain', 'muscle_weakness', 'stiff_neck',
    'swelling_joints', 'movement_stiffness', 'spinning_movements', 'loss_of_balance',
    'unsteadiness', 'weakness_of_one_body_side', 'loss_of_smell', 'bladder_discomfort',
    'foul_smell_of urine', 'continuous_feel_of_urine', 'passage_of_gases', 'internal_itching',
    'toxic_look_(typhos)', 'depression', 'irritability', 'muscle_pain', 'altered_sensorium',
    'red_spots_over_body', 'belly_pain', 'abnormal_menstruation', 'dischromic _patches',
    'watering_from_eyes', 'increased_appetite', 'polyuria', 'family_history', 'mucoid_sputum',
    'rusty_sputum', 'lack_of_concentration', 'visual_disturbances', 'receiving_blood_transfusion',
    'receiving_unsterile_injections', 'coma', 'stomach_bleeding', 'distention_of_abdomen',
    'history_of_alcohol_consumption', 'fluid_overload', 'blood_in_sputum', 'prominent_veins_on_calf',
    'palpitations', 'painful_walking', 'pus_filled_pimples', 'blackheads', 'scurring',
    'skin_peeling', 'silver_like_dusting', 'small_dents_in_nails', 'inflammatory_nails',
    'blister', 'red_sore_around_nose', 'yellow_crust_ooze'
]

MEDICAL_DISCLAIMER = (
    "Preliminary decision-support result. This is an algorithmic prediction "
    "and not a medical diagnosis. The consulting doctor remains solely "
    "responsible for clinical evaluation and diagnosis."
)

class MLServiceError(Exception):
    """Base exception for ML service failures."""
    pass

class MLValidationError(MLServiceError):
    """Raised when symptom input is invalid or unsupported."""
    pass

class MLModelUnavailableError(MLServiceError):
    """Raised when the pre-trained model file cannot be loaded."""
    pass


def clean_label(symptom_key: str) -> str:
    """Generate a clean, professional human-readable label from symptom key."""
    special_cases = {
        'spotting_ urination': 'Spotting Urination',
        'foul_smell_of urine': 'Foul Smell Of Urine',
        'dischromic _patches': 'Dischromic Patches',
        'cold_hands_and_feets': 'Cold Hands And Feet',
        'toxic_look_(typhos)': 'Toxic Look (Typhus)',
        'scurring': 'Skin Scarring',
    }
    if symptom_key in special_cases:
        return special_cases[symptom_key]
    cleaned = ' '.join(symptom_key.replace('_', ' ').split()).title()
    return cleaned


# Authoritative mapping of all variations (raw, clean, normalized) to model vector indices
SYMPTOM_INDEX_MAP = {}
for idx, sym in enumerate(RAW_SYMPTOMS):
    # Map exact raw key
    if sym not in SYMPTOM_INDEX_MAP:
        SYMPTOM_INDEX_MAP[sym] = [idx]
    else:
        SYMPTOM_INDEX_MAP[sym].append(idx)

    # Map normalized version (spaces removed around underscores, lowercased)
    norm_snake = '_'.join(sym.replace('_', ' ').split()).lower()
    if norm_snake not in SYMPTOM_INDEX_MAP:
        SYMPTOM_INDEX_MAP[norm_snake] = [idx]
    elif idx not in SYMPTOM_INDEX_MAP[norm_snake]:
        SYMPTOM_INDEX_MAP[norm_snake].append(idx)

    # Map plain space separated
    norm_space = ' '.join(sym.replace('_', ' ').split()).lower()
    if norm_space not in SYMPTOM_INDEX_MAP:
        SYMPTOM_INDEX_MAP[norm_space] = [idx]
    elif idx not in SYMPTOM_INDEX_MAP[norm_space]:
        SYMPTOM_INDEX_MAP[norm_space].append(idx)

    # Map display label
    lbl = clean_label(sym).lower()
    if lbl not in SYMPTOM_INDEX_MAP:
        SYMPTOM_INDEX_MAP[lbl] = [idx]
    elif idx not in SYMPTOM_INDEX_MAP[lbl]:
        SYMPTOM_INDEX_MAP[lbl].append(idx)

# Special cases normalization
SYMPTOM_INDEX_MAP['spotting_urination'] = [13]
SYMPTOM_INDEX_MAP['dischromic_patches'] = [102]
SYMPTOM_INDEX_MAP['foul_smell_of_urine'] = [90]
SYMPTOM_INDEX_MAP['cold_hands_and_feet'] = [17]
SYMPTOM_INDEX_MAP['skin_scarring'] = [124]


# Sorted list of unique symptoms for flat display: [(raw_key, label), ...]
_seen_keys = set()
FRONTEND_SYMPTOMS = []
for sym in sorted(RAW_SYMPTOMS, key=lambda s: clean_label(s)):
    label = clean_label(sym)
    if label not in _seen_keys:
        _seen_keys.add(label)
        FRONTEND_SYMPTOMS.append((sym, label))


# Clinical body-system categories for intuitive practitioner navigation
SYMPTOM_CATEGORIES = {
    'Skin & Dermatology': [
        'itching', 'skin_rash', 'nodal_skin_eruptions', 'dischromic _patches',
        'pus_filled_pimples', 'blackheads', 'scurring', 'skin_peeling',
        'silver_like_dusting', 'blister', 'red_sore_around_nose', 'yellow_crust_ooze',
        'red_spots_over_body', 'bruising', 'small_dents_in_nails', 'inflammatory_nails',
        'brittle_nails'
    ],
    'Respiratory & ENT': [
        'continuous_sneezing', 'chills', 'cough', 'breathlessness', 'phlegm',
        'throat_irritation', 'sinus_pressure', 'runny_nose', 'congestion',
        'patches_in_throat', 'mucoid_sputum', 'rusty_sputum', 'blood_in_sputum',
        'loss_of_smell', 'redness_of_eyes', 'sunken_eyes', 'watering_from_eyes',
        'pain_behind_the_eyes'
    ],
    'Gastrointestinal & Hepatic': [
        'stomach_pain', 'acidity', 'ulcers_on_tongue', 'vomiting', 'indigestion',
        'nausea', 'loss_of_appetite', 'constipation', 'abdominal_pain', 'diarrhoea',
        'acute_liver_failure', 'swelling_of_stomach', 'pain_during_bowel_movements',
        'pain_in_anal_region', 'bloody_stool', 'irritation_in_anus', 'passage_of_gases',
        'internal_itching', 'belly_pain', 'stomach_bleeding', 'distention_of_abdomen',
        'yellowish_skin', 'yellowing_of_eyes', 'excessive_hunger', 'increased_appetite'
    ],
    'Neurological & Sensory': [
        'anxiety', 'mood_swings', 'restlessness', 'headache', 'dizziness',
        'slurred_speech', 'spinning_movements', 'loss_of_balance', 'unsteadiness',
        'weakness_of_one_body_side', 'depression', 'irritability', 'altered_sensorium',
        'lack_of_concentration', 'visual_disturbances', 'blurred_and_distorted_vision',
        'coma', 'toxic_look_(typhos)'
    ],
    'Musculoskeletal': [
        'joint_pain', 'muscle_wasting', 'weakness_in_limbs', 'neck_pain', 'cramps',
        'knee_pain', 'hip_joint_pain', 'muscle_weakness', 'stiff_neck', 'swelling_joints',
        'movement_stiffness', 'muscle_pain', 'painful_walking', 'back_pain'
    ],
    'Urinary & Reproductive': [
        'burning_micturition', 'spotting_ urination', 'dark_urine', 'yellow_urine',
        'bladder_discomfort', 'foul_smell_of urine', 'continuous_feel_of_urine',
        'polyuria', 'abnormal_menstruation', 'extra_marital_contacts'
    ],
    'Systemic & General': [
        'shivering', 'fatigue', 'weight_gain', 'cold_hands_and_feets', 'weight_loss', 'lethargy',
        'irregular_sugar_level', 'high_fever', 'mild_fever', 'sweating', 'dehydration',
        'fluid_overload', 'swelled_lymph_nodes', 'malaise', 'chest_pain',
        'fast_heart_rate', 'obesity', 'swollen_legs', 'swollen_blood_vessels',
        'puffy_face_and_eyes', 'enlarged_thyroid', 'swollen_extremeties',
        'drying_and_tingling_lips', 'family_history', 'receiving_blood_transfusion',
        'receiving_unsterile_injections', 'history_of_alcohol_consumption',
        'prominent_veins_on_calf', 'palpitations'
    ]
}

# Structured list of categorized symptoms for frontend rendering
FRONTEND_CATEGORIZED_SYMPTOMS = []
for category_name, sym_keys in SYMPTOM_CATEGORIES.items():
    cat_items = []
    for k in sym_keys:
        cat_items.append((k, clean_label(k)))
    cat_items.sort(key=lambda x: x[1])
    FRONTEND_CATEGORIZED_SYMPTOMS.append({
        'name': category_name,
        'symptoms': cat_items
    })


# Thread-safe model singleton caching
_CACHED_MODEL = None
_MODEL_LOCK = threading.Lock()

def get_ml_model():
    """
    Load and return the pre-trained ML model singleton.
    Thread-safe and cached in memory across requests.
    Raises MLModelUnavailableError if the model file is missing or corrupted.
    """
    global _CACHED_MODEL
    if _CACHED_MODEL is not None:
        return _CACHED_MODEL

    with _MODEL_LOCK:
        if _CACHED_MODEL is not None:
            return _CACHED_MODEL

        model_path = Path(settings.BASE_DIR) / 'trained_model'
        if not model_path.exists():
            logger.error("Pre-trained model file not found at expected location: %s", model_path)
            raise MLModelUnavailableError("Disease prediction model is currently not configured on this server.")

        try:
            loaded = joblib.load(model_path)
            _CACHED_MODEL = loaded
            logger.info("Successfully loaded ML decision-support model (version %s)", MODEL_VERSION)
            return _CACHED_MODEL
        except Exception as exc:
            logger.exception("Failed to deserialize pre-trained ML model: %s", str(exc))
            raise MLModelUnavailableError("Failed to initialize decision-support model.")


def validate_and_normalize_symptoms(selected_symptoms):
    """
    Validate, normalize, and de-duplicate incoming symptom strings.
    Ensures input is safe, non-empty, within size bounds, and maps only to supported symptoms.

    Returns:
        tuple of (active_indices: set of int, clean_display_labels: list of str)
    Raises:
        MLValidationError: if input is empty, oversized, or contains no valid symptoms.
    """
    if not selected_symptoms:
        raise MLValidationError("Please select at least one clinical symptom.")

    if not isinstance(selected_symptoms, (list, tuple, set)):
        raise MLValidationError("Invalid symptom input format.")

    if len(selected_symptoms) > MAX_SYMPTOM_SELECTION_LIMIT:
        raise MLValidationError(f"Too many symptoms selected. Maximum allowed is {MAX_SYMPTOM_SELECTION_LIMIT}.")

    active_indices = set()
    cleaned_display_labels = []
    seen_labels = set()

    for item in selected_symptoms:
        if not isinstance(item, str):
            continue

        raw = item.strip().lower()
        if not raw:
            continue

        # Look up in index map
        indices = None
        matched_canonical = None

        if raw in SYMPTOM_INDEX_MAP:
            indices = SYMPTOM_INDEX_MAP[raw]
        else:
            # Fallback normalized search
            norm = '_'.join(raw.replace('_', ' ').split())
            if norm in SYMPTOM_INDEX_MAP:
                indices = SYMPTOM_INDEX_MAP[norm]

        if indices:
            for idx in indices:
                active_indices.add(idx)

            label = clean_label(RAW_SYMPTOMS[indices[0]])
            if label not in seen_labels:
                seen_labels.add(label)
                cleaned_display_labels.append(label)

    if not active_indices or not cleaned_display_labels:
        raise MLValidationError("None of the submitted symptoms are recognized by the clinical model.")

    return active_indices, sorted(cleaned_display_labels)


def build_feature_vector(active_indices):
    """
    Constructs the exact 132-dimension binary feature vector expected by the model.
    """
    vector = [0] * len(RAW_SYMPTOMS)
    for idx in active_indices:
        if 0 <= idx < len(vector):
            vector[idx] = 1
    return vector


def predict_from_symptoms(selected_symptoms, top_k=3):
    """
    Executes the clinical decision support prediction pipeline:
    1. Input Validation & De-duplication
    2. Symptom Normalization & Whitelist Verification
    3. 132-dimension Feature Vector Construction
    4. Model Inference & Probability Calculation
    5. Result Validation & Differential Diagnosis Extraction
    6. Medical Disclaimer and Response Packaging

    Returns a standardized dictionary. Never exposes internal tracebacks or system paths.
    """
    # Check for empty or invalid input upfront
    if not selected_symptoms:
        return {
            'success': False,
            'predicted_disease': None,
            'confidence_score': 0,
            'differential_diagnosis': [],
            'symptoms_selected': [],
            'disclaimer': MEDICAL_DISCLAIMER,
            'error': "Please select at least one clinical symptom."
        }

    try:
        active_indices, clean_labels = validate_and_normalize_symptoms(selected_symptoms)
    except MLValidationError as err:
        return {
            'success': False,
            'predicted_disease': None,
            'confidence_score': 0,
            'differential_diagnosis': [],
            'symptoms_selected': [],
            'disclaimer': MEDICAL_DISCLAIMER,
            'error': str(err)
        }

    try:
        model = get_ml_model()
    except MLModelUnavailableError as err:
        logger.error("Decision support model unavailable: %s", str(err))
        return {
            'success': False,
            'predicted_disease': None,
            'confidence_score': 0,
            'differential_diagnosis': [],
            'symptoms_selected': clean_labels,
            'disclaimer': MEDICAL_DISCLAIMER,
            'error': "Decision-support service is temporarily unavailable. Please proceed with clinical evaluation."
        }

    try:
        feature_vector = build_feature_vector(active_indices)
        input_data = [feature_vector]

        # Model prediction
        predicted = model.predict(input_data)
        predicted_disease = str(predicted[0]).strip()

        # Posterior probability distribution
        probabilities = model.predict_proba(input_data)[0]
        max_proba = float(probabilities.max()) * 100.0
        confidence = round(max_proba, 1)

        # Build top-k differential diagnosis possibilities
        top_k = min(top_k, len(model.classes_))
        sorted_indices = probabilities.argsort()[-top_k:][::-1]
        differentials = []
        for idx in sorted_indices:
            cond_name = str(model.classes_[idx]).strip()
            cond_pct = round(float(probabilities[idx]) * 100.0, 1)
            differentials.append({
                'condition': cond_name,
                'probability': cond_pct,
            })

        return {
            'success': True,
            'predicted_disease': predicted_disease,
            'confidence_score': confidence,
            'differential_diagnosis': differentials,
            'symptoms_selected': clean_labels,
            'disclaimer': MEDICAL_DISCLAIMER,
            'model_version': MODEL_VERSION,
            'error': None
        }

    except Exception as exc:
        logger.exception("Unexpected error during ML inference: %s", str(exc))
        return {
            'success': False,
            'predicted_disease': None,
            'confidence_score': 0,
            'differential_diagnosis': [],
            'symptoms_selected': clean_labels,
            'disclaimer': MEDICAL_DISCLAIMER,
            'error': "An error occurred while evaluating symptoms. Please try again."
        }
