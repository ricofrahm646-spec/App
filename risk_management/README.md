# Risk Management

Hard invariants implemented by the initial JARVIS risk engine:

- maximum one open trade at a time;
- no simultaneous buy and sell exposure;
- force-close path when a position reaches the configured 20% loss threshold;
- lot sizing based on account balance, risk percentage, stop distance and point value.

These checks are shared by paper trading and MT5 live adapters.
