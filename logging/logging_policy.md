# Logging Policy

- structured application logs (service, action, severity, timestamp)
- exception traces for failed operations
- trade lifecycle event logs (open/modify/close)
- risk intervention audit trail
- reconnect attempts and integration failures

Sensitive fields (tokens, keys) must be redacted before persistence.
