# Logging

JARVIS keeps a dedicated logging folder for deployment artifacts and operational runbooks.

The Python package intentionally avoids using `logging` as an import package name because it
would shadow the Python standard library module. Runtime logging configuration belongs in
`backend/app` and emitted logs should be routed to the deployment platform or mounted volumes.
