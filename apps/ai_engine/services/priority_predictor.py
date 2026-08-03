from apps.service_desk.services.ai_service import AIService


class PriorityPredictor:
    @staticmethod
    def predict(company, text: str):
        return AIService.suggest_priority(company, text.lower())
