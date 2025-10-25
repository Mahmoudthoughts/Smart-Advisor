import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../environments/environment';

export interface WatchlistSymbol {
  readonly id: number;
  readonly symbol: string;
  readonly created_at: string;
  readonly latest_close: number | null;
  readonly latest_close_date: string | null;
}

export interface PortfolioTransaction {
  readonly id: number;
  readonly symbol: string;
  readonly type: string;
  readonly quantity: number;
  readonly price: number;
  readonly fee: number;
  readonly tax: number;
  readonly currency: string;
  readonly trade_datetime: string;
  readonly account?: string | null;
  readonly notes?: string | null;
  readonly notional_value: number;
}

export interface TimelineSnapshot {
  readonly symbol: string;
  readonly date: string;
  readonly shares_open: number;
  readonly market_value_base: number;
  readonly cost_basis_open_base: number;
  readonly unrealized_pl_base: number;
  readonly realized_pl_to_date_base: number;
  readonly hypo_liquidation_pl_base: number;
  readonly day_opportunity_base: number;
  readonly peak_hypo_pl_to_date_base: number;
  readonly drawdown_from_peak_pct: number;
}

export interface TimelinePricePoint {
  readonly date: string;
  readonly adj_close: number;
}

export interface TimelineTransaction {
  readonly id: number;
  readonly symbol: string;
  readonly type: string;
  readonly quantity: number;
  readonly price: number;
  readonly trade_datetime: string;
  readonly account?: string | null;
  readonly notional_value: number;
}

export interface TimelineResponse {
  readonly symbol: string;
  readonly snapshots: TimelineSnapshot[];
  readonly prices: TimelinePricePoint[];
  readonly transactions: TimelineTransaction[];
}

export interface TransactionPayload {
  readonly symbol: string;
  readonly type: string;
  readonly quantity: number;
  readonly price: number;
  readonly trade_datetime: string;
  readonly fee?: number;
  readonly tax?: number;
  readonly currency?: string;
  readonly account?: string | null;
  readonly notes?: string | null;
}

@Injectable({ providedIn: 'root' })
export class PortfolioDataService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  getWatchlist(): Observable<WatchlistSymbol[]> {
    return this.http.get<WatchlistSymbol[]>(`${this.baseUrl}/portfolio/watchlist`);
  }

  addWatchlistSymbol(symbol: string): Observable<WatchlistSymbol> {
    return this.http.post<WatchlistSymbol>(`${this.baseUrl}/portfolio/watchlist`, { symbol });
  }

  getTransactions(): Observable<PortfolioTransaction[]> {
    return this.http.get<PortfolioTransaction[]>(`${this.baseUrl}/portfolio/transactions`);
  }

  createTransaction(payload: TransactionPayload): Observable<PortfolioTransaction> {
    return this.http.post<PortfolioTransaction>(`${this.baseUrl}/portfolio/transactions`, payload);
  }

  getTimeline(symbol: string, from?: string, to?: string): Observable<TimelineResponse> {
    let params = new HttpParams();
    if (from) {
      params = params.set('from', from);
    }
    if (to) {
      params = params.set('to', to);
    }
    return this.http.get<TimelineResponse>(`${this.baseUrl}/symbols/${symbol}/timeline`, { params });
  }
}
