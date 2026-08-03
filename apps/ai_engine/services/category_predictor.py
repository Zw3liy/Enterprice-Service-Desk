from apps.service_desk.services.ai_service import AIService


class CategoryPredictor:
    @staticmethod
    def predict(text: str) -> str:
        return AIService.suggest_category_code(text.lower())
