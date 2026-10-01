from django.test import TestCase
from Doctor.ml_service import predict_from_symptoms, RAW_SYMPTOMS, MODEL_FEATURE_COUNT, MAX_SYMPTOM_SELECTION_LIMIT


class MLClinicalDecisionSupportTests(TestCase):
    def test_feature_vector_dimension(self):
        """Feature vector must match exactly 132 symptoms recognized by the model."""
        self.assertEqual(len(RAW_SYMPTOMS), 132)
        self.assertEqual(MODEL_FEATURE_COUNT, 132)

    def test_valid_symptoms_prediction_and_confidence(self):
        """Predict disease with valid symptoms returns expected classification and positive confidence."""
        symptoms = ['itching', 'skin_rash', 'nodal_skin_eruptions']
        result = predict_from_symptoms(symptoms)
        self.assertTrue(result['success'])
        self.assertIsNotNone(result['predicted_disease'])
        self.assertGreater(result['confidence_score'], 0.0)
        self.assertIn('Fungal infection', result['predicted_disease'])

    def test_disclaimer_present_in_all_predictions(self):
        """Predictions must include a prominent clinical decision-support disclaimer."""
        result = predict_from_symptoms(['chills', 'vomiting'])
        self.assertTrue(result['success'])
        self.assertIn('disclaimer', result)
        self.assertIn('decision-support', result['disclaimer'].lower())
        self.assertIn('not a medical diagnosis', result['disclaimer'].lower())

    def test_empty_symptoms_handled_gracefully(self):
        """Empty input does not raise exceptions and returns None prediction."""
        result = predict_from_symptoms([])
        self.assertFalse(result['success'])
        self.assertIsNone(result['predicted_disease'])
        self.assertEqual(result['confidence_score'], 0.0)

    def test_duplicate_symptoms_deduplicated(self):
        """Duplicate symptoms submitted in payload are automatically deduplicated."""
        result = predict_from_symptoms(['headache', 'headache', 'chills', 'chills'])
        self.assertTrue(result['success'])
        # Only unique formatted symptoms in returned list
        self.assertEqual(len(result['symptoms_selected']), 2)

    def test_exceeding_max_symptoms_rejected(self):
        """Supplying more symptoms than MAX_SYMPTOM_SELECTION_LIMIT returns validation error."""
        too_many = RAW_SYMPTOMS[:MAX_SYMPTOM_SELECTION_LIMIT + 3]
        result = predict_from_symptoms(too_many)
        self.assertFalse(result['success'])
        self.assertIn(f"Maximum allowed is {MAX_SYMPTOM_SELECTION_LIMIT}", result['error'])

    def test_differential_diagnosis_ordering_and_probabilities(self):
        """Differential diagnosis returns top-k possibilities sorted by probability descending."""
        symptoms = ['joint_pain', 'vomiting', 'fatigue', 'high_fever']
        result = predict_from_symptoms(symptoms, top_k=3)
        self.assertTrue(result['success'])
        diffs = result.get('differential_diagnosis', [])
        self.assertGreaterEqual(len(diffs), 1)

        # Check descending order of probabilities
        probs = [d['probability'] for d in diffs]
        self.assertEqual(probs, sorted(probs, reverse=True))
