import unittest

from app.services.risk_engine import RiskEngine, TradeState


class RiskEngineTests(unittest.TestCase):
    def test_rejects_opposite_side_entry(self) -> None:
        engine = RiskEngine()

        decision = engine.evaluate_entry(existing_side="buy", requested_side="sell")

        self.assertFalse(decision.allow_entry)
        self.assertIn("Simultaneous buy and sell", decision.reason)

    def test_force_closes_large_loser(self) -> None:
        engine = RiskEngine()

        decision = engine.evaluate_live_state(
            TradeState(side="buy", live_trades=1, unrealized_loss_percent=20.0)
        )

        self.assertTrue(decision.should_force_close)
        self.assertIn("Loss threshold", decision.reason)


if __name__ == "__main__":
    unittest.main()
