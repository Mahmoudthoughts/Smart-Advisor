import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../environments/environment';

export type DecisionAction = 'BUY_MORE' | 'TRIM' | 'EXIT' | 'HOLD';
export type DecisionStatus = 'OPEN' | 'EXECUTED' | 'SKIPPED';

export interface InvestmentDecisionOutcome {
  readonly price_change: number | null;
  readonly price_change_pct: number | null;
  readonly projected_value_change: number | null;
}

export interface InvestmentDecision {
  readonly id: number;
  readonly portfolio_id: number | null;
  readonly investor: string;
  readonly symbol: string;
  readonly action: DecisionAction;
  readonly planned_quantity: number | null;
  readonly decision_price: number | null;
  readonly decision_at: string;
  readonly status: DecisionStatus;
  readonly resolved_at: string | null;
  readonly resolved_price: number | null;
  readonly actual_quantity: number | null;
  readonly outcome_price: number | null;
  readonly notes: string | null;
  readonly outcome_notes: string | null;
  readonly outcome: InvestmentDecisionOutcome;
}

export interface InvestmentDecisionCreatePayload {
  readonly investor: string;
  readonly symbol: string;
  readonly action: DecisionAction;
  readonly planned_quantity?: number | null;
  readonly decision_price?: number | null;
  readonly decision_at?: string | null;
  readonly notes?: string | null;
  readonly portfolio_id?: number | null;
}

export interface InvestmentDecisionResolvePayload {
  readonly status: DecisionStatus;
  readonly resolved_at?: string | null;
  readonly resolved_price?: number | null;
  readonly actual_quantity?: number | null;
  readonly outcome_price?: number | null;
  readonly outcome_notes?: string | null;
}

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
  readonly series: MonteCarloSeries | null;
  readonly ai_selected_params?: Record<string, number> | null;
  readonly ai_score_breakdown?: Record<string, number> | null;
}

export interface MonteCarloRequestPayload {
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

  runMonteCarlo(payload: MonteCarloRequestPayload): Observable<MonteCarloResponse> {
    return this.http.post<MonteCarloResponse>(`${this.baseUrl}/risk/montecarlo/run`, payload);
  }

  deleteTransaction(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/portfolio/transactions/${id}`);
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

  getDecisions(params?: {
    readonly symbol?: string | null;
    readonly investor?: string | null;
    readonly status?: DecisionStatus | null;
  }): Observable<InvestmentDecision[]> {
    let query = new HttpParams();
    if (params?.symbol) {
      query = query.set('symbol', params.symbol);
    }
    if (params?.investor) {
      query = query.set('investor', params.investor);
    }
    if (params?.status) {
      query = query.set('status', params.status);
    }
    return this.http.get<InvestmentDecision[]>(`${this.baseUrl}/decisions`, { params: query });
  }

  logDecision(payload: InvestmentDecisionCreatePayload): Observable<InvestmentDecision> {
    return this.http.post<InvestmentDecision>(`${this.baseUrl}/decisions`, payload);
  }

  resolveDecision(id: number, payload: InvestmentDecisionResolvePayload): Observable<InvestmentDecision> {
    return this.http.put<InvestmentDecision>(`${this.baseUrl}/decisions/${id}`, payload);
  }
}
