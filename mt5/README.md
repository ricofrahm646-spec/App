# MT5 Connector Notes

This directory is reserved for MT5-side helpers, terminal automation scripts, and environment-specific installation hooks.

The backend currently exposes a safety-focused MT5 connector abstraction that:

- blocks simultaneous Buy/Sell exposure,
- blocks more than one active trade,
- supports emergency-close decisions when loss thresholds are breached.

Live terminal automation still requires MT5 to be installed on the target machine together with valid credentials and terminal paths.
