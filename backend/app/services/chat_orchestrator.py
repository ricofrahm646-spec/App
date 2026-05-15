from app.models.chat import ChatAction, ChatMessageResponse


class ChatOrchestrator:
    """
    Interprets natural language intents and maps them to module actions.
    In production, this service can call an LLM + tool execution layer.
    """

    def process_message(self, message: str) -> ChatMessageResponse:
        lowered = message.lower()
        actions: list[ChatAction] = []

        if "gold" in lowered or "xau" in lowered:
            actions.append(
                ChatAction(
                    action="generate_strategy",
                    target_module="strategies",
                    description="Neue Gold-Scalping-Strategie erstellen.",
                )
            )
        if "optimiere" in lowered or "optimize" in lowered:
            actions.append(
                ChatAction(
                    action="optimize_strategy",
                    target_module="ai",
                    description="Strategie mit Optuna/RL Pipeline optimieren.",
                )
            )
        if "telegram" in lowered:
            actions.append(
                ChatAction(
                    action="configure_notifications",
                    target_module="telegram",
                    description="Telegram Signal-Bridge aktualisieren.",
                )
            )
        if "trailing stop" in lowered:
            actions.append(
                ChatAction(
                    action="extend_risk_logic",
                    target_module="risk_management",
                    description="Trailing-Stop Regel in Risiko-Engine aktivieren.",
                )
            )

        if not actions:
            actions.append(
                ChatAction(
                    action="analyze_request",
                    target_module="ai",
                    description="Anfrage analysieren und passende Module vorschlagen.",
                )
            )

        return ChatMessageResponse(
            summary="Anfrage analysiert und modulare Aktionen geplant.",
            actions=actions,
        )
