import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { mapHistogramSeries } from '../shared/chart-utils';
import { TvChartComponent, TvSeries } from '../shared/tv-chart/tv-chart.component';

import {
  MonteCarloRequestPayload,
  MonteCarloResponse,
  MonteCarloService,
} from '../services/montecarlo.service';

@Component({
  selector: 'app-montecarlo-page',
  standalone: true,
  imports: [CommonModule, FormsModule, TvChartComponent],
  templateUrl: './montecarlo.component.html',
  styleUrls: ['./montecarlo.component.scss']
})
export class MontecarloComponent {
  private readonly monteCarloService = inject(MonteCarloService);

  readonly symbol = signal<string>('');
  readonly startingCapital = signal<number>(5000);
  readonly tradesPerRun = signal<number>(500);
  readonly simulations = signal<number>(5000);
  readonly winRate = signal<number>(0.596);
  readonly avgWin = signal<number>(320);
  readonly avgLoss = signal<number>(-168);
  readonly slippagePct = signal<number>(0);
  readonly feePerTrade = signal<number>(0);
  readonly useAi = signal<boolean>(true);

  readonly isLoading = signal<boolean>(false);
  readonly loadError = signal<string | null>(null);
  readonly results = signal<MonteCarloResponse | null>(null);

  readonly finalReturnsSeries = signal<TvSeries[]>([]);
  readonly maxDrawdownsSeries = signal<TvSeries[]>([]);

  readonly requestPayload = computed<MonteCarloRequestPayload>(() => ({
    symbol: this.normalizeSymbol(this.symbol()) || undefined,
    starting_capital: this.cleanNumber(this.startingCapital(), 5000),
    runs: this.cleanInteger(this.simulations(), 5000),
    trades_per_run: this.cleanInteger(this.tradesPerRun(), 500),
    win_rate: this.cleanNumber(this.winRate(), 0.5),
    avg_win: this.cleanNumber(this.avgWin(), 0),
    avg_loss: Math.abs(this.cleanNumber(this.avgLoss(), 0)),
    risk_multiplier: 1.0,
    fee_per_trade: Math.max(this.cleanNumber(this.feePerTrade(), 0), 0),
    slippage_pct: Math.max(this.cleanNumber(this.slippagePct(), 0), 0),
    include_series: true,
    use_ai: this.useAi(),
  }));

  runSimulation(): void {
    this.isLoading.set(true);
    this.loadError.set(null);
    this.monteCarloService.runMonteCarlo(this.requestPayload()).subscribe({
      next: (response) => {
        this.results.set(response);
        this.updateCharts(response);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.results.set(null);
        this.resetCharts();
        const detail = err?.error?.detail;
        this.loadError.set(
          typeof detail === 'string'
            ? detail
            : 'Unable to run the Monte Carlo simulation. Please try again.'
        );
        this.isLoading.set(false);
      }
    });
  }

  formatPercent(value: number | null | undefined, digits = 1): string {
    if (value === null || value === undefined || !Number.isFinite(value)) {
      return '—';
    }
    return `${value.toFixed(digits)}%`;
  }

  formatProbability(value: number | null | undefined, digits = 1): string {
    if (value === null || value === undefined || !Number.isFinite(value)) {
      return '—';
    }
    return `${(value * 100).toFixed(digits)}%`;
  }

  toNumber(value: string | number, fallback = 0): number {
    const parsed = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  toInteger(value: string | number, fallback = 1): number {
    const parsed = typeof value === 'number' ? value : Number(value);
    if (!Number.isFinite(parsed)) {
      return fallback;
    }
    return Math.max(1, Math.round(parsed));
  }

  normalizeSymbol(value: string): string {
    return value.trim().toUpperCase();
  }

  private updateCharts(response: MonteCarloResponse): void {
    const series = response.series;
    if (!series) {
      this.resetCharts();
      return;
    }

    const finalHistogram = this.buildHistogram(series.final_returns, 28);
    const drawdownHistogram = this.buildHistogram(series.max_drawdowns, 28);

    this.finalReturnsSeries.set([
      {
        type: 'histogram',
        data: mapHistogramSeries(finalHistogram.counts, undefined, '#38bdf8'),
        options: { priceFormat: { type: 'volume' } }
      }
    ]);
    this.maxDrawdownsSeries.set([
      {
        type: 'histogram',
        data: mapHistogramSeries(drawdownHistogram.counts, undefined, '#ef4444'),
        options: { priceFormat: { type: 'volume' } }
      }
    ]);
  }

  private resetCharts(): void {
    this.finalReturnsSeries.set([]);
    this.maxDrawdownsSeries.set([]);
  }

  private buildHistogram(values: number[], binCount: number): { labels: string[]; counts: number[] } {
    if (!values.length) {
      return { labels: [], counts: [] };
    }

    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const step = span / binCount;
    const counts = new Array(binCount).fill(0);

    values.forEach((value) => {
      const normalized = (value - min) / span;
      const index = Math.min(binCount - 1, Math.max(0, Math.floor(normalized * binCount)));
      counts[index] += 1;
    });

    const labels = Array.from({ length: binCount }, (_, index) => {
      const start = min + step * index;
      const end = start + step;
      return `${start.toFixed(1)}%–${end.toFixed(1)}%`;
    });

    return { labels, counts };
  }

  private cleanNumber(value: number, fallback: number): number {
    return Number.isFinite(value) ? value : fallback;
  }

  private cleanInteger(value: number, fallback: number): number {
    if (!Number.isFinite(value)) {
      return fallback;
    }
    return Math.max(1, Math.round(value));
  }
}
