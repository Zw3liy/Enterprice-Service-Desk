from apps.service_desk.services.ai_service import AIService


class ClassifierService:
    @staticmethod
    def classify(text: str) -> dict:
        return AIService.classify_text(text)
