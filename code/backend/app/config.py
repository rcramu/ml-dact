"""Central configuration for the Continuous Training Pipeline backend."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://ctp_user:ctp_pass@postgres:5432/continuous_training"
    random_seed: int = 42

    mlflow_tracking_uri: str = "http://mlflow:5000"
    mlflow_experiment: str = "continuous-training"

    # synthetic customer-churn tabular dataset (paper Section 7.1)
    baseline_rows: int = 1500
    expected_volume: int = 1500
    volume_anomaly_tolerance: float = 0.20  # req.md Sec. 30 "Expected +/- 20%"

    # PyTorch trainer (req.md Sec. 15-16)
    train_epochs: int = 120
    train_batch_size: int = 32
    train_learning_rate: float = 0.01
    hidden_dim_1: int = 16
    hidden_dim_2: int = 8

    # Evaluation / regression gate (req.md Sec. 16, 21-23)
    minimum_f1: float = 0.70
    minimum_recall: float = 0.60
    minimum_precision: float = 0.60
    max_regression_pct: float = 10.0

    class Config:
        env_prefix = "CTP_"


settings = Settings()
