# AI Module

The AI layer is intentionally provider-neutral. The backend can call these
interfaces to combine:

- PyTorch/TensorFlow models for market regime classification
- XGBoost feature models
- Optuna optimization jobs
- genetic search over strategy parameters
- reinforcement-learning environments for execution policies

All models must report observed validation metrics only. No fixed win-rate
claims are encoded in this project.
