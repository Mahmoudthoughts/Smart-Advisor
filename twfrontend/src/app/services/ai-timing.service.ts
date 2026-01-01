import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
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

export type AiTimingHistoryEntry = {
  id: number;
  symbol: string;
  symbol_name?: string | null;
  bar_size: string;
  duration_days: number;
  timezone: string;
  use_rth: boolean;
  created_at: string;
  request_payload: Record<string, unknown>;
  response_payload: Record<string, unknown>;
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

  getTimingHistory(params: {
    readonly symbol?: string;
    readonly startDate?: string;
    readonly endDate?: string;
    readonly limit?: number;
    readonly offset?: number;
  }): Observable<AiTimingHistoryEntry[]> {
    let query = new HttpParams();
    if (params.symbol) {
      query = query.set('symbol', params.symbol);
    }
    if (params.startDate) {
      query = query.set('start_date', params.startDate);
    }
    if (params.endDate) {
      query = query.set('end_date', params.endDate);
    }
    if (params.limit) {
      query = query.set('limit', String(params.limit));
    }
    if (params.offset) {
      query = query.set('offset', String(params.offset));
    }
    return this.http.get<AiTimingHistoryEntry[]>(`${this.baseUrl}/ai/timing/history`, { params: query });
  }
}
