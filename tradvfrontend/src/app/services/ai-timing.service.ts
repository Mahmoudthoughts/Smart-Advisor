import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { Observable } from 'rxjs';

export type AiTimingCitation = {
  id: string;
  text: string;
};

export type AiTimingResponse = {
  summary: string;
  best_buy_window: string;
  best_sell_window: string;
  confidence: number;
  citations: AiTimingCitation[];
  features: Record<string, unknown>;
};

export type AiTimingRequest = {
  symbol: string;
  bar_size: string;
  duration_days: number;
  timezone: string;
  use_rth: boolean;
  force_refresh?: boolean;
  symbol_name?: string | null;
  session_summaries?: Array<{
    date: string;
    bars: number;
    open: number | null;
    midday_low: number | null;
    close: number | null;
    drawdown_pct: number | null;
    recovery_pct: number | null;
  }>;
  bars: Array<{
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume?: number | null;
  }>;
};

@Injectable({ providedIn: 'root' })
export class AiTimingService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  getTiming(payload: AiTimingRequest): Observable<AiTimingResponse> {
    return this.http.post<AiTimingResponse>(`${this.baseUrl}/ai/timing`, payload);
  }
}
