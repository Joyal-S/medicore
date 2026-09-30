"""
ML Disease Prediction Service for PAWCARE.
Maintains exact 132-feature vector order required by the pre-trained MultinomialNB model
while providing clean display names and robust input handling.
"""

from pathlib import Path
from django.conf import settings
import joblib

# EXACT 132-symptom feature order expected by the trained model
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

def clean_label(symptom_key):
    """Generate a clean, professional human-readable label from symptom key."""
    # Handle known inconsistent symptom strings gracefully
    special_cases = {
        'spotting_ urination': 'Spotting Urination',
        'foul_smell_of urine': 'Foul Smell Of Urine',
        'dischromic _patches': 'Dischromic Patches',
        'cold_hands_and_feets': 'Cold Hands And Feet',
        'toxic_look_(typhos)': 'Toxic Look (Typhus)',
    }
    if symptom_key in special_cases:
        return special_cases[symptom_key]
    # Clean underscores and excess spaces
    cleaned = ' '.join(symptom_key.replace('_', ' ').split()).title()
    return cleaned

# Mapping for fast lookup: maps both raw and normalized symptom names to model vector index
SYMPTOM_INDEX_MAP = {}
for idx, sym in enumerate(RAW_SYMPTOMS):
    SYMPTOM_INDEX_MAP[sym] = idx
    # Also support normalized version
    normalized = '_'.join(sym.replace('_', ' ').split())
    SYMPTOM_INDEX_MAP[normalized] = idx

# Sorted list of unique symptoms for frontend display: [(key, label), ...]
_seen_keys = set()
FRONTEND_SYMPTOMS = []
for sym in sorted(RAW_SYMPTOMS, key=lambda s: clean_label(s)):
    label = clean_label(sym)
    if label not in _seen_keys:
        _seen_keys.add(label)
        FRONTEND_SYMPTOMS.append((sym, label))

_CACHED_MODEL = None

def get_ml_model():
    """Load and cache the pre-trained ML model using settings.BASE_DIR."""
    global _CACHED_MODEL
    if _CACHED_MODEL is None:
        model_path = Path(settings.BASE_DIR) / 'trained_model'
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found at {model_path}")
        _CACHED_MODEL = joblib.load(model_path)
    return _CACHED_MODEL

MEDICAL_DISCLAIMER = (
    "Preliminary decision-support result. This is an algorithmic prediction "
    "and not a medical diagnosis. The consulting doctor remains solely "
    "responsible for clinical evaluation and diagnosis."
)

def predict_from_symptoms(selected_symptoms):
    """
    Takes a list of selected symptom names, extracts the 132-element feature vector,
    and returns prediction results with confidence and medical disclaimer.
    """
    if not selected_symptoms:
        return {
            'predicted_disease': None,
            'confidence_score': 0,
            'symptoms_selected': [],
            'disclaimer': MEDICAL_DISCLAIMER,
        }

    model = get_ml_model()
    testingsymptoms = [0] * len(RAW_SYMPTOMS)

    cleaned_selected_labels = []
    for symptom in selected_symptoms:
        # Check in index map
        if symptom in SYMPTOM_INDEX_MAP:
            idx = SYMPTOM_INDEX_MAP[symptom]
            testingsymptoms[idx] = 1
            cleaned_selected_labels.append(clean_label(symptom))
        else:
            # Fallback normalized match
            norm = '_'.join(symptom.replace('_', ' ').split())
            if norm in SYMPTOM_INDEX_MAP:
                idx = SYMPTOM_INDEX_MAP[norm]
                testingsymptoms[idx] = 1
                cleaned_selected_labels.append(clean_label(norm))

    input_data = [testingsymptoms]
    predicted = model.predict(input_data)
    proba = model.predict_proba(input_data).max() * 100
    confidence = round(float(proba), 1)

    predicted_disease = str(predicted[0])

    return {
        'predicted_disease': predicted_disease,
        'confidence_score': confidence,
        'symptoms_selected': cleaned_selected_labels,
        'disclaimer': MEDICAL_DISCLAIMER,
    }
