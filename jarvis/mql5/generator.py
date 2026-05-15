import os

class MQL5Generator:
    def __init__(self, output_dir="jarvis/mql5/experts"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_ea(self, name, logic_code):
        template = f"""
//+------------------------------------------------------------------+
//|                                              {name}.mq5 |
//|                                  Copyright 2024, JARVIS AI |
//|                                             https://jarvis.ai |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024, JARVIS AI"
#property link      "https://jarvis.ai"
#property version   "1.00"
#property strict

input double Risk = 1.0;
input int SL = 100;
input int TP = 200;

int OnInit() {{
   Print("JARVIS Expert {name} Initialized");
   return(INIT_SUCCEEDED);
}}

void OnDeinit(const int reason) {{
   Print("JARVIS Expert {name} Deinitialized");
}}

void OnTick() {{
   {logic_code}
}}
"""
        filepath = os.path.join(self.output_dir, f"{name}.mq5")
        with open(filepath, "w") as f:
            f.write(template)
        return filepath
