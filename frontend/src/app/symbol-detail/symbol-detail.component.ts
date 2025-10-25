import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CurrencyPipe, PercentPipe } from '@angular/common';
import type { EChartsOption } from 'echarts';
import { NgxEchartsDirective } from 'ngx-echarts';
import { Subscription } from 'rxjs';

import {
  PortfolioDataService,
  SymbolRefreshResponse,
  TimelinePricePoint,
  TimelineSnapshot,
  TimelineTransaction,
  WatchlistSymbol
} from '../portfolio-data.service';

interface SymbolSummary {
  readonly lastPrice: number | null;
  readonly change: number | null;
  readonly changePercent: number | null;
  readonly positionQty: number | null;
  readonly averageCost: number | null;
  readonly unrealized: number | null;
  readonly realized: number | null;
  readonly hypo: number | null;
}

@Component({
  selector: 'app-symbol-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, NgxEchartsDirective, CurrencyPipe, PercentPipe],
  templateUrl: './symbol-detail.component.html',
  styleUrls: ['./symbol-detail.component.scss']
})
export class SymbolDetailComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly dataService = inject(PortfolioDataService);

  private paramSub: Subscription | null = null;

  readonly symbol = signal<string>('');
  readonly isLoading = signal<boolean>(false);
  readonly loadError = signal<string | null>(null);
  readonly refreshStatus = signal<string | null>(null);
  readonly refreshError = signal<string | null>(null);
  readonly watchlistEntry = signal<WatchlistSymbol | null>(null);
  readonly snapshots = signal<TimelineSnapshot[]>([]);
  readonly prices = signal<TimelinePricePoint[]>([]);
  readonly transactions = signal<TimelineTransaction[]>([]);

  readonly chartOption = signal<EChartsOption>({
    tooltip: { trigger: 'axis' },
    legend: { data: ['Hypo P&L', 'Realized P&L', 'Unrealized P&L', 'Price', 'Average Cost', 'Trades'] },
    grid: { left: 32, right: 24, top: 32, bottom: 48 },
    xAxis: { type: 'category', boundaryGap: false, data: [] },
    yAxis: [
      {
        type: 'value',
        axisLabel: { formatter: (value: number) => `$${value.toLocaleString()}` }
      },
      {
        type: 'value',
        position: 'right',
        axisLabel: { formatter: (value: number) => `$${value.toFixed(2)}` }
      }
    ],
    series: []
  });

  readonly summary = computed<SymbolSummary>(() => {
    const entry = this.watchlistEntry();
    const snaps = this.snapshots();
    const lastSnapshot = snaps.length ? snaps[snaps.length - 1] : null;
    return {
      lastPrice: entry?.latest_close ?? null,
      change: entry?.day_change ?? null,
      changePercent: entry?.day_change_percent ?? null,
      positionQty: lastSnapshot ? Number(lastSnapshot.shares_open) : entry?.position_qty ?? null,
      averageCost:
        lastSnapshot && lastSnapshot.shares_open > 0
          ? Number(lastSnapshot.cost_basis_open_base) / Number(lastSnapshot.shares_open)
          : entry?.average_cost ?? null,
      unrealized: lastSnapshot ? Number(lastSnapshot.unrealized_pl_base) : entry?.unrealized_pl ?? null,
      realized: lastSnapshot ? Number(lastSnapshot.realized_pl_to_date_base) : null,
      hypo: lastSnapshot ? Number(lastSnapshot.hypo_liquidation_pl_base) : null
    };
  });

  ngOnInit(): void {
    this.paramSub = this.route.paramMap.subscribe((params) => {
      const symbol = (params.get('symbol') ?? '').toUpperCase();
      this.symbol.set(symbol);
      this.loadWatchlist();
      this.loadTimeline();
    });
  }

  ngOnDestroy(): void {
    this.paramSub?.unsubscribe();
  }

  loadWatchlist(): void {
    this.dataService.getWatchlist().subscribe({
      next: (items) => {
        const entry = items.find((item) => item.symbol === this.symbol());
        this.watchlistEntry.set(entry ?? null);
      },
      error: () => this.watchlistEntry.set(null)
    });
  }

  loadTimeline(): void {
    const ticker = this.symbol();
    if (!ticker) {
      return;
    }
    this.isLoading.set(true);
    this.loadError.set(null);
    this.dataService.getTimeline(ticker).subscribe({
      next: (response) => {
        this.snapshots.set(response.snapshots);
        this.prices.set(response.prices);
        this.transactions.set(response.transactions);
        this.updateChart();
        this.isLoading.set(false);
      },
      error: () => {
        this.snapshots.set([]);
        this.prices.set([]);
        this.transactions.set([]);
        this.updateChart();
        this.isLoading.set(false);
        this.loadError.set('Unable to load analytics for this symbol.');
      }
    });
  }

  refresh(): void {
    const ticker = this.symbol();
    if (!ticker) {
      return;
    }
    this.refreshStatus.set(null);
    this.refreshError.set(null);
    this.dataService.refreshSymbol(ticker).subscribe({
      next: (response: SymbolRefreshResponse) => {
        this.refreshStatus.set(
          `${response.symbol} refreshed (${response.prices_ingested} prices, ${response.snapshots_rebuilt} snapshots).`
        );
        this.loadWatchlist();
        this.loadTimeline();
      },
      error: (err) => {
        const message = err?.error?.detail ?? 'Unable to refresh market data for this symbol.';
        this.refreshError.set(message);
      }
    });
  }

  private updateChart(): void {
    const snapshots = this.snapshots();
    const prices = this.prices();
    const transactions = this.transactions();
    if (!snapshots.length && !prices.length) {
      this.chartOption.update((option) => ({
        ...option,
        xAxis: { ...option.xAxis, data: [] },
        series: []
      }));
      return;
    }

    const axisDates = snapshots.length ? snapshots.map((snapshot) => snapshot.date) : prices.map((price) => price.date);
    const hypoSeries = snapshots.map((snapshot) => Number(snapshot.hypo_liquidation_pl_base));
    const realizedSeries = snapshots.map((snapshot) => Number(snapshot.realized_pl_to_date_base));
    const unrealizedSeries = snapshots.map((snapshot) => Number(snapshot.unrealized_pl_base));
    const priceSeries = prices.map((point) => Number(point.adj_close));
    const averageCostSeries = snapshots.length
      ? snapshots.map((snapshot) =>
          snapshot.shares_open > 0
            ? Number(snapshot.cost_basis_open_base) / Number(snapshot.shares_open)
            : null
        )
      : axisDates.map(() => null);

    const tradeMarkers = transactions.map((tx) => {
      const tradeDate = tx.trade_datetime.split('T')[0];
      const markerColor = tx.type === 'SELL' ? '#dc2626' : '#16a34a';
      return {
        name: tx.type,
        value: [tradeDate, Number(tx.price)],
        symbol: 'triangle',
        symbolRotate: tx.type === 'SELL' ? 180 : 0,
        symbolSize: Math.max(12, Math.min(32, Math.abs(tx.quantity) * 1.5)),
        itemStyle: { color: markerColor },
        tx
      };
    });

    let latestSnapshot: TimelineSnapshot | null = null;
    if (snapshots.length > 0) {
      latestSnapshot = snapshots[snapshots.length - 1];
    }

    const realizedMarkers: Array<{
      coord: [string, number];
      value: number;
      itemStyle: { color: string };
      label: { formatter: () => string };
    }> = [];
    if (snapshots.length > 1) {
      let previousRealized = Number(snapshots[0].realized_pl_to_date_base);
      for (let i = 1; i < snapshots.length; i += 1) {
        const snapshot = snapshots[i];
        const delta = Number(snapshot.realized_pl_to_date_base) - previousRealized;
        const date = snapshot.date;
        const sellsForDay = transactions.filter((tx) => tx.type === 'SELL' && tx.trade_datetime.startsWith(date));
        if (sellsForDay.length > 0 && Math.abs(delta) > 0.01) {
          realizedMarkers.push({
            coord: [date, Number(snapshot.realized_pl_to_date_base)],
            value: delta,
            itemStyle: { color: delta >= 0 ? '#16a34a' : '#dc2626' },
            label: {
              formatter: () => `${delta >= 0 ? '▲' : '▼'} $${delta.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
            }
          });
        }
        previousRealized = Number(snapshot.realized_pl_to_date_base);
      }
    }

    const legendFormatter = (name: string) => {
      if (!latestSnapshot) {
        return name;
      }
      if (name === 'Unrealized P&L') {
        const value = Number(latestSnapshot.unrealized_pl_base).toLocaleString(undefined, { maximumFractionDigits: 0 });
        return `${name} ($${value})`;
      }
      if (name === 'Realized P&L') {
        const value = Number(latestSnapshot.realized_pl_to_date_base).toLocaleString(undefined, { maximumFractionDigits: 0 });
        return `${name} ($${value})`;
      }
      return name;
    };

    this.chartOption.set({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        formatter: (params: any) => {
          const entries = Array.isArray(params) ? params : [params];
          const dateLabel = entries[0]?.axisValueLabel ?? '';
          const lines = entries
            .filter((entry: any) => entry.seriesName !== 'Trades')
            .map((entry: any) => {
              const value = Number(entry.data).toLocaleString(undefined, {
                maximumFractionDigits: entry.seriesName === 'Price' ? 2 : 0
              });
              const prefix = entry.seriesName === 'Price' ? '$' : '$';
              return `${entry.marker} ${entry.seriesName}: ${prefix}${value}`;
            });
          const tradesForDay = transactions.filter((tx) => tx.trade_datetime.startsWith(dateLabel));
          tradesForDay.forEach((tx) => {
            const direction = tx.type === 'SELL' ? 'Sold' : 'Bought';
            const value = (tx.quantity * tx.price).toLocaleString(undefined, { maximumFractionDigits: 2 });
            const feePart = tx.fee ? `, fees $${tx.fee.toFixed(2)}` : '';
            lines.push(
              `${tx.type === 'SELL' ? '🔻' : '🔺'} ${direction} ${tx.quantity} @ $${tx.price.toFixed(2)} (≈ $${value}${feePart})`
            );
          });
          return [`<strong>${dateLabel}</strong>`, ...lines].join('<br/>');
        }
      },
      legend: {
        data: ['Hypo P&L', 'Realized P&L', 'Unrealized P&L', 'Price', 'Average Cost', 'Trades'],
        formatter: legendFormatter
      },
      grid: { left: 32, right: 24, top: 32, bottom: 48 },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: axisDates
      },
      yAxis: [
        {
          type: 'value',
          axisLabel: {
            formatter: (value: number) => `$${value.toLocaleString()}`
          }
        },
        {
          type: 'value',
          position: 'right',
          axisLabel: {
            formatter: (value: number) => `$${value.toFixed(2)}`
          }
        }
      ],
      series: [
        {
          name: 'Hypo P&L',
          type: 'line',
          smooth: true,
          symbol: 'circle',
          areaStyle: { opacity: 0.12 },
          data: hypoSeries
        },
        {
          name: 'Realized P&L',
          type: 'line',
          smooth: true,
          symbol: 'none',
          stack: 'pnl',
          areaStyle: { opacity: 0.1 },
          lineStyle: { width: 1.5 },
          data: realizedSeries,
          markPoint: { data: realizedMarkers }
        },
        {
          name: 'Unrealized P&L',
          type: 'line',
          smooth: true,
          stack: 'pnl',
          areaStyle: { opacity: 0.1 },
          data: unrealizedSeries
        },
        {
          name: 'Price',
          type: 'line',
          smooth: true,
          yAxisIndex: 1,
          lineStyle: { width: 2, type: 'dashed' },
          data: priceSeries
        },
        {
          name: 'Average Cost',
          type: 'line',
          step: 'end',
          connectNulls: false,
          showSymbol: false,
          yAxisIndex: 1,
          lineStyle: { width: 1.5, color: '#f59e0b' },
          data: averageCostSeries
        },
        {
          name: 'Trades',
          type: 'scatter',
          yAxisIndex: 1,
          data: tradeMarkers,
          tooltip: {
            formatter: (param: any) => {
              const tx = param.data.tx;
              const value = Number(tx.quantity * tx.price).toFixed(2);
              const feeNote = tx.fee ? `<br/>Fees: $${Number(tx.fee).toFixed(2)}` : '';
              const accountNote = tx.account ? `<br/>Account: ${tx.account}` : '';
              const notes = tx.notes ? `<br/>Notes: ${tx.notes}` : '';
              return `${param.seriesName}: ${param.name} ${tx.quantity} @ $${Number(tx.price).toFixed(2)}<br/>Value: $${value}${feeNote}${accountNote}${notes}`;
            }
          }
        }
      ]
    });
  }
}
