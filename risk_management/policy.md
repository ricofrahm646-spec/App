# JARVIS Risk Policy

Default risk constraints are intentionally conservative:

1. One open trade at a time.
2. No simultaneous buy and sell exposure.
3. Position size is calculated from account equity, stop distance and risk %.
4. Risk per trade is capped at 5% by validation, with a 1% default.
5. Open trades at or beyond 20% loss relative to account balance trigger an
   emergency-close action.
6. Strategy metrics must be reported from observed backtests only; fabricated
   win rates or profit claims are forbidden.
