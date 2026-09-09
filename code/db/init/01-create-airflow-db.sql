-- Runs once against the default dact_training database on first init.
-- Creates a second database for Airflow's own metadata store (LocalExecutor),
-- reusing the same postgres container/user rather than running a second DB.
CREATE DATABASE airflow OWNER dact_user;
