from apps.service_desk.services.ai_service import AIService


class SummarizerService:
    @staticmethod
    def summarize(title: str, description: str) -> str:
        return AIService.summarize(title, description)
