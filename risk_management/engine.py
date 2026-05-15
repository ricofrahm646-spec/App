def calculate_lot_size(balance: float, risk_percent: float, stop_loss_points: float, point_value: float) -> float:
    if stop_loss_points <= 0 or point_value <= 0:
        return 0.0
    risk_amount = balance * (risk_percent / 100)
    lots = risk_amount / (stop_loss_points * point_value)
    return round(max(lots, 0.01), 2)
