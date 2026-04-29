export type VariableName =
  | "t2m_celsius"
  | "wind_speed_10m_ms"
  | "wind_direction_10m_deg"
  | "msl_hpa"
  | "tp_6h_mm"
  | "toa_wm2"

export type SourceName = "era5" | "graphcast" | "arome"

export type TimeRange = "1d" | "7d" | "14d"

export type ForecastHorizon = 6 | 12 | 18 | 24

export interface TimeseriesPoint {
  timestamp: string
  era5: number | null
  graphcast: number | null
  arome: number | null
}

export interface TimeseriesResponse {
  lat: number
  lon: number
  days: number
  variables: {
    [key in VariableName]?: TimeseriesPoint[]
  }
}

export interface MaeMetrics {
  latest: number | null
  avg_7d: number | null
  rmse_latest: number | null
  bias_latest: number | null
}

export interface MaeComparisonResponse {
  horizon: ForecastHorizon
  evaluation_date: string
  comparisons: {
    graphcast_vs_era5: { [key in VariableName]?: MaeMetrics }
    arome_vs_era5: { [key in VariableName]?: MaeMetrics }
  }
}

export interface GridPoint {
  lat: number
  lon: number
}

export interface ForecastGridPoint {
  lat: number
  lon: number
  value: number | null
}

export interface ForecastGridResponse {
  date: string
  hour: number
  source: SourceName
  variable: VariableName
  points: ForecastGridPoint[]
}
