const uiPort = import.meta.env.VITE_PUBLIC_UI_PORT || '3066'
const apiPort = import.meta.env.VITE_PUBLIC_API_PORT || '8166'
const pgPort = import.meta.env.VITE_PUBLIC_PG_PORT || '5476'
const pgDb = import.meta.env.VITE_PUBLIC_PG_DB || 'dact_training'
const mlflowPort = import.meta.env.VITE_PUBLIC_MLFLOW_PORT || '5026'
const airflowPort = import.meta.env.VITE_PUBLIC_AIRFLOW_PORT || '8766'

export const stackConfig = {
  uiPort, apiPort, pgPort, pgDb, mlflowPort, airflowPort,
  uiUrl: `http://localhost:${uiPort}`,
  apiUrl: `http://localhost:${apiPort}`,
  mlflowUrl: `http://localhost:${mlflowPort}`,
  airflowUrl: `http://localhost:${airflowPort}`,
}

