from jarvis.mql5.generator import MQL5Generator
from jarvis.risk_management.engine import RiskEngine

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
        else:
            return {"status": "info", "message": "Kommando erkannt. JARVIS analysiert...", "command": command}

    def _handle_bot_creation(self, command: str):
        bot_name = "NeuralBot_" + command.split()[-1].capitalize()
        logic = "// AI Generated Logic\n   if(iRSI(Symbol(),0,14,PRICE_CLOSE,0) < 30) OrderSend(Symbol(),OP_BUY,0.1,Ask,3,0,0);"
        filepath = self.generator.generate_ea(bot_name, logic)
        return {
            "status": "success",
            "message": f"Bot '{bot_name}' wurde erstellt.",
            "path": filepath,
            "action": "Generated MQL5 code and expert advisor file."
        }
