class RiskEngine:
    def __init__(self, daily_drawdown_limit=4.0):
        self.daily_drawdown_limit = daily_drawdown_limit
        self.locked = False

    def validate_trade(self, current_balance, current_equity, potential_risk):
        if self.locked:
            return False, "Trading Locked: Drawdown Limit Reached"

        current_dd = ((current_balance - current_equity) / current_balance) * 100
        if current_dd >= self.daily_drawdown_limit:
            self.locked = True
            return False, "Drawdown limit exceeded. System locked."

        # Rule: Max 1 trade simultaneously (simplified check)
        # Rule: Stop trading at 20% loss on a single trade
        if potential_risk > (current_balance * 0.20):
             return False, "Risk per trade exceeds 20% limit."

        return True, "Validated"

    def calculate_lot_size(self, balance, risk_percent, sl_pips):
        risk_amount = balance * (risk_percent / 100)
        # Assuming standard lot (100k) and 1 pip = $10 for 1 lot
        pip_value = 10.0
        if sl_pips == 0: return 0.01
        lot_size = risk_amount / (sl_pips * pip_value)
        return round(lot_size, 2)
