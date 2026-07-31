from django.test import TestCase
from apps.escalation_engine.services import EscalationEngine
class EscTests(TestCase):
    def test_open(self):
        self.assertEqual(list(EscalationEngine.open_escalations()), [])
