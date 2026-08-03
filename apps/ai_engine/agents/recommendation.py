from apps.service_desk.services.ai_service import AIService


class RecommendationAgent:
    @staticmethod
    def for_ticket(ticket, limit: int = 5):
        return AIService.recommend_articles(ticket, limit=limit)
