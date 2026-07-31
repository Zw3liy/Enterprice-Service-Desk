from apps.service_desk.services.ai_service import AIService


class SentimentService:
    @staticmethod
    def score(text: str) -> float:
        return AIService.score_sentiment(text)
