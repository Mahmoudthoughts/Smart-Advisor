import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';

export interface MonteCarloPercentiles {
  readonly p5: number;
  readonly p25: number;
  readonly p50: number;
  readonly p75: number;
  readonly p95: number;
}

export interface MonteCarloSeries {
  readonly final_returns: number[];
  readonly max_drawdowns: number[];
}

export interface MonteCarloResponse {
  readonly final_return_pct: MonteCarloPercentiles;
  readonly max_drawdown_pct: MonteCarloPercentiles;
  readonly probability_ruin: number;
  readonly probability_max_drawdown_over_30: number;
  readonly series?: MonteCarloSeries | null;
  readonly ai_selected_params?: Record<string, number> | null;
  readonly ai_score_breakdown?: Record<string, number> | null;
}

export interface MonteCarloRequestPayload {
  readonly symbol?: string;
  readonly lookback_days?: number;
  readonly starting_capital: number;
  readonly runs: number;
  readonly trades_per_run: number;
  readonly win_rate: number;
  readonly avg_win: number;
  readonly avg_loss: number;
  readonly risk_multiplier?: number;
  readonly fee_per_trade?: number;
  readonly slippage_pct?: number;
  readonly include_series?: boolean;
  readonly use_ai?: boolean;
}

@Injectable({ providedIn: 'root' })
export class MonteCarloService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  runMonteCarlo(payload: MonteCarloRequestPayload): Observable<MonteCarloResponse> {
    return this.http.post<MonteCarloResponse>(`${this.baseUrl}/risk/montecarlo/run`, payload);
  }
}
