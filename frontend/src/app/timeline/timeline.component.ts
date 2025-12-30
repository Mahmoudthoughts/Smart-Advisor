import { CommonModule } from '@angular/common';

import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import type { EChartsOption, MarkPointComponentOption } from 'echarts';

type TimelineMarkPoint = NonNullable<MarkPointComponentOption['data']>[number];
import { NgxEchartsDirective } from 'ngx-echarts';

import {
  PortfolioDataService,
  TimelinePricePoint,
  TimelineResponse,
  TimelineSnapshot,
  TimelineTransaction,
  WatchlistSymbol,
} from '../portfolio-data.service';

@Component({
  selector: 'app-timeline-page',
  standalone: true,
  imports: [CommonModule, FormsModule, NgxEchartsDirective],
  templateUrl: './timeline.component.html',
  styleUrls: ['./timeline.component.scss']
})
export class TimelineComponent implements OnInit {
  private readonly dataService = inject(PortfolioDataService);

  readonly watchlist = signal<WatchlistSymbol[]>([]);
  readonly selectedSymbol = signal<string>('');
  readonly fromDate = signal<string>('');
  readonly toDate = signal<string>('');
  readonly selectedPreset = signal<string | null>(null);
  readonly snapshots = signal<TimelineSnapshot[]>([]);
  readonly prices = signal<TimelinePricePoint[]>([]);
  readonly transactions = signal<TimelineTransaction[]>([]);
  readonly isLoading = signal<boolean>(false);
  readonly loadError = signal<string | null>(null);

  readonly tableRows = computed(() => {
    const priceLookup = new Map(this.prices().map((point) => [point.date, point.adj_close]));
    return this.snapshots().map((snapshot) => ({
      date: snapshot.date,
      price: priceLookup.get(snapshot.date) ?? null,
      sharesOpen: snapshot.shares_open,
      marketValue: snapshot.market_value_base,
      costBasis: snapshot.cost_basis_open_base,
      hypoPnl: snapshot.hypo_liquidation_pl_base,
      realizedPnl: snapshot.realized_pl_to_date_base,
      unrealizedPnl: snapshot.unrealized_pl_base,
      dayOpportunity: snapshot.day_opportunity_base,
      peakHypoPnl: snapshot.peak_hypo_pl_to_date_base,
      drawdownPct: snapshot.drawdown_from_peak_pct,
    }));
  });

  readonly hasData = computed(() => this.snapshots().length > 0 || this.prices().length > 0);

  readonly timelineOption = signal<EChartsOption>({
    tooltip: { trigger: 'axis' },
    legend: { data: ['Hypo P&L', 'Realized P&L', 'Unrealized P&L', 'Price', 'Average Cost', 'Trades'] },
    grid: { left: 32, right: 24, top: 32, bottom: 48 },
    xAxis: { type: 'category', boundaryGap: false, data: [] },
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
    series: []
  });

  ngOnInit(): void {
    this.loadWatchlist();
  }

  loadWatchlist(): void {
    this.dataService.getWatchlist().subscribe({
      next: (symbols) => {
        this.loadError.set(null);
        this.watchlist.set(symbols);
        if (!this.selectedSymbol() && symbols.length > 0) {
          this.selectedSymbol.set(symbols[0].symbol);
          this.loadTimeline();
        }
      },
      error: () => {
        this.loadError.set('Unable to load watchlist. Add a symbol to begin tracking.');
      }
    });
  }

  loadTimeline(): void {
    const symbol = this.selectedSymbol();
    if (!symbol) {
      return;
    }
    this.isLoading.set(true);
    this.loadError.set(null);
    this.dataService
      .getTimeline(symbol, this.fromDate() || undefined, this.toDate() || undefined)
      .subscribe({
        next: (response: TimelineResponse) => {
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
          this.loadError.set('Unable to load timeline data for the selected symbol.');
        }
      });
  }

  // Quick date range presets
  applyPreset(preset: 'WTD' | 'MTD' | 'LAST_WEEK' | 'LAST_MONTH' | 'LAST_3M'): void {
    const today = this.atMidnight(new Date());
    let from: Date;
    let to: Date = today;

    switch (preset) {
      case 'WTD': {
        from = this.startOfWeek(today);
        break;
      }
      case 'MTD': {
        from = this.startOfMonth(today);
        break;
      }
      case 'LAST_WEEK': {
        const lastWeekEnd = this.addDays(this.startOfWeek(today), -1);
        const lastWeekStart = this.addDays(this.startOfWeek(today), -7);
        from = lastWeekStart;
        to = lastWeekEnd;
        break;
      }
      case 'LAST_MONTH': {
        const firstOfThisMonth = this.startOfMonth(today);
        const lastOfLastMonth = this.addDays(firstOfThisMonth, -1);
        from = this.startOfMonth(lastOfLastMonth);
        to = lastOfLastMonth;
        break;
      }
      case 'LAST_3M': {
        from = this.addMonths(today, -3);
        break;
      }
    }

    this.selectedPreset.set(preset);
    this.fromDate.set(this.formatDate(from));
    this.toDate.set(this.formatDate(to));
    this.loadTimeline();
  }

  // When user changes dates manually, clear preset selection
  onFromChange(value: string): void {
    this.selectedPreset.set(null);
    this.fromDate.set(value);
  }

  onToChange(value: string): void {
    this.selectedPreset.set(null);
    this.toDate.set(value);
  }

  private atMidnight(d: Date): Date {
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }

  private startOfWeek(d: Date): Date {
    // Monday as start of week
    const day = d.getDay(); // 0 (Sun) .. 6 (Sat)
    const diff = (day + 6) % 7; // days since Monday
    return this.atMidnight(this.addDays(d, -diff));
  }

  private startOfMonth(d: Date): Date {
    return new Date(d.getFullYear(), d.getMonth(), 1);
  }

  private addDays(d: Date, days: number): Date {
    const result = new Date(d);
    result.setDate(result.getDate() + days);
    return this.atMidnight(result);
  }

  private addMonths(d: Date, months: number): Date {
    const year = d.getFullYear();
    const month = d.getMonth();
    const day = d.getDate();
    const result = new Date(year, month + months, day);
    return this.atMidnight(result);
  }

  private formatDate(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  onSymbolChange(symbol: string): void {
    this.selectedSymbol.set(symbol);
    this.loadTimeline();
  }

  updateChart(): void {
    const snapshots = this.snapshots();
    const prices = this.prices();
    const transactions = this.transactions();
    if (!snapshots.length && !prices.length) {
      this.timelineOption.update((option) => ({
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

    const realizedMarkers: TimelineMarkPoint[] = [];
    if (snapshots.length > 1) {
      let previousRealized = Number(snapshots[0].realized_pl_to_date_base);
      for (let i = 1; i < snapshots.length; i += 1) {
        const snapshot = snapshots[i];
        const delta = Number(snapshot.realized_pl_to_date_base) - previousRealized;
        const date = snapshot.date;
        const sellsForDay = transactions.filter((tx) => tx.type === 'SELL' && tx.trade_datetime.startsWith(date));
        if (sellsForDay.length > 0 && Math.abs(delta) > 0.01) {
          realizedMarkers.push({
            name: delta >= 0 ? 'Realized Gain' : 'Realized Loss',
            coord: [date, Number(snapshot.realized_pl_to_date_base)],
            value: delta,
            itemStyle: { color: delta >= 0 ? '#16a34a' : '#dc2626' },
            label: {
              formatter: () =>
                `${delta >= 0 ? '+' : '-'} $${delta.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
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

    this.timelineOption.set({
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
              `${direction} ${tx.quantity} @ $${tx.price.toFixed(2)} (~ $${value}${feePart})`
            );
          });
          return [`<strong>${dateLabel}</strong>`, ...lines].join('<br/>');
        }
      },
      legend: { data: ['Hypo P&L', 'Realized P&L', 'Unrealized P&L', 'Price', 'Average Cost', 'Trades'], formatter: legendFormatter },
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
