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
  readonly previous_close: number | null;
  readonly day_change: number | null;
  readonly day_change_percent: number | null;
  readonly position_qty: number | null;
  readonly average_cost: number | null;
  readonly unrealized_pl: number | null;
  readonly name: string | null;
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
  readonly account_id?: number | null;
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
  readonly fee: number;
  readonly tax: number;
  readonly account_id?: number | null;
  readonly account?: string | null;
  readonly notes?: string | null;
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
  readonly account_id?: number | null;
  readonly account?: string | null;
  readonly notes?: string | null;
}

export interface PortfolioAccount {
  readonly id: number;
  readonly name: string;
  readonly type?: string | null;
  readonly currency: string;
  readonly notes?: string | null;
  readonly is_default: boolean;
  readonly created_at: string;
}

export interface PortfolioAccountPayload {
  readonly name: string;
  readonly type?: string | null;
  readonly currency?: string;
  readonly notes?: string | null;
  readonly is_default?: boolean;
}

export interface SymbolSearchResult {
  readonly symbol: string;
  readonly name: string;
  readonly region?: string | null;
  readonly currency?: string | null;
  readonly match_score?: number | null;
}

export interface SymbolRefreshResponse {
  readonly symbol: string;
  readonly prices_ingested: number;
  readonly snapshots_rebuilt: number;
}

@Injectable({ providedIn: 'root' })
export class PortfolioDataService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  getWatchlist(): Observable<WatchlistSymbol[]> {
    return this.http.get<WatchlistSymbol[]>(`${this.baseUrl}/portfolio/watchlist`);
  }

  addWatchlistSymbol(symbol: string, name?: string | null): Observable<WatchlistSymbol> {
    const payload: Record<string, unknown> = { symbol };
    if (name) {
      payload['name'] = name;
    }
    return this.http.post<WatchlistSymbol>(`${this.baseUrl}/portfolio/watchlist`, payload);
  }

  getTransactions(): Observable<PortfolioTransaction[]> {
    return this.http.get<PortfolioTransaction[]>(`${this.baseUrl}/portfolio/transactions`);
  }

  createTransaction(payload: TransactionPayload): Observable<PortfolioTransaction> {
    return this.http.post<PortfolioTransaction>(`${this.baseUrl}/portfolio/transactions`, payload);
  }

  updateTransaction(id: number, payload: TransactionPayload): Observable<PortfolioTransaction> {
    return this.http.put<PortfolioTransaction>(`${this.baseUrl}/portfolio/transactions/${id}`, payload);
  }

  getAccounts(): Observable<PortfolioAccount[]> {
    return this.http.get<PortfolioAccount[]>(`${this.baseUrl}/accounts`);
  }

  createAccount(payload: PortfolioAccountPayload): Observable<PortfolioAccount> {
    return this.http.post<PortfolioAccount>(`${this.baseUrl}/accounts`, payload);
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

  searchSymbols(query: string): Observable<SymbolSearchResult[]> {
    const params = new HttpParams().set('query', query);
    return this.http.get<SymbolSearchResult[]>(`${this.baseUrl}/symbols/search`, { params });
  }

  refreshSymbol(symbol: string): Observable<SymbolRefreshResponse> {
    return this.http.post<SymbolRefreshResponse>(`${this.baseUrl}/symbols/${symbol}/refresh`, {});
  }
}
