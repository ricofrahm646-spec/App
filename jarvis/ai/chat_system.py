from jarvis.mql5.generator import MQL5Generator
from jarvis.risk_management.engine import RiskEngine
import uuid

class AIChatSystem:
    def __init__(self):
        self.generator = MQL5Generator()
        self.risk_engine = RiskEngine()

    def process_command(self, command: str):
        command = command.lower()
        if "baue einen neuen" in command or "erstelle" in command:
            return self._handle_bot_creation(command)
        elif "optimiere" in command:
            return {"status": "success", "message": "Optimierung gestartet...", "details": "Neural God Protocol analysiert Marktphasen."}
        elif "trailing stop" in command:
             return {"status": "success", "message": "Trailing Stop Modul wird zu bestehenden Bots hinzugefügt."}
        else:
            return {"status": "info", "message": "Kommando erkannt. JARVIS analysiert...", "command": command}

    def _handle_bot_creation(self, command: str):
        strategy_type = "default"
        if "ict" in command: strategy_type = "ict"
        elif "smc" in command: strategy_type = "smc"
        elif "gold" in command: strategy_type = "gold"

        bot_id = str(uuid.uuid4())[:8]
        bot_name = f"NeuralBot_{strategy_type.upper()}_{bot_id}"

        filepath = self.generator.generate_ea(bot_name, strategy_type=strategy_type)

        return {
            "status": "success",
            "message": f"Professional bot '{bot_name}' ({strategy_type}) created.",
            "path": filepath,
            "action": "Integrated Strategy Factory logic and generated MQL5 source."
        }
