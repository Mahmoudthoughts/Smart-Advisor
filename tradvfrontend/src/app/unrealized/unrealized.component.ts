import { CommonModule, CurrencyPipe, DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { businessDayToString, parseDateString } from '../shared/chart-utils';
import { TvChartComponent, TvSeries } from '../shared/tv-chart/tv-chart.component';

type LotType = 'REAL' | 'HYPOTHETICAL';

interface Lot {
  readonly id: string;
  readonly ticker: string;
  readonly type: LotType;
  readonly buyDate: string;
  readonly shares: number;
  readonly buyPrice: number;
}

interface LotForm {
  ticker: string;
  buyDate: string;
  shares: number;
  buyPrice: number;
  type: LotType;
}

interface ReportRow {
  date: string;
  sellPrice: number;
  profitValue: number;
  profitPct: number;
  marketValue: number;
}

interface TargetSelection {
  date: string;
  profit: number;
  targetPrice: number;
}

@Component({
  selector: 'app-unrealized',
  standalone: true,
  imports: [CommonModule, FormsModule, CurrencyPipe, DecimalPipe, DatePipe, TvChartComponent],
  templateUrl: './unrealized.component.html',
  styleUrls: ['./unrealized.component.scss']
})
export class UnrealizedComponent {
  readonly lots = signal<Lot[]>([
    {
      id: 'seed-real',
      ticker: 'AAPL',
      type: 'REAL',
      buyDate: this.toDateInput(new Date()),
      shares: 12,
      buyPrice: 172.5
    },
    {
      id: 'seed-hypo',
      ticker: 'AAPL',
      type: 'HYPOTHETICAL',
      buyDate: this.toDateInput(new Date()),
      shares: 5,
      buyPrice: 180
    }
  ]);

  readonly newLot = signal<LotForm>({
    ticker: 'AAPL',
    buyDate: this.toDateInput(new Date()),
    shares: 10,
    buyPrice: 170,
    type: 'REAL'
  });

  readonly includeHypothetical = signal<boolean>(true);
  readonly overrideShares = signal<number | null>(null);
  readonly costMode = signal<'FIFO' | 'LIFO' | 'AVERAGE_COST'>('AVERAGE_COST');
  readonly reportRows = signal<ReportRow[]>([]);
  readonly loadError = signal<string | null>(null);
  readonly target = signal<TargetSelection | null>(null);

  readonly tickers = computed(() => {
    const set = new Set(this.lots().map((lot) => lot.ticker));
    return Array.from(set).sort();
  });

  readonly selectedTicker = signal<string>('AAPL');

  readonly totalShares = computed(() => {
    return this.activeLots().reduce((acc, lot) => acc + lot.shares, 0);
  });

  readonly averageCost = computed(() => {
    const lots = this.activeLots();
    const cost = lots.reduce((acc, lot) => acc + lot.buyPrice * lot.shares, 0);
    const shares = lots.reduce((acc, lot) => acc + lot.shares, 0);
    if (!shares) {
      return 0;
    }
    return cost / shares;
  });

  readonly sharesForChart = computed(() => {
    const override = this.overrideShares();
    if (override && override > 0) {
      return override;
    }
    return this.totalShares();
  });

  readonly chartSeries = computed<TvSeries[]>(() => {
    const rows = this.reportRows();
    const baseDates = rows.map((row) => parseDateString(row.date));
    return [
      {
        type: 'area',
        data: baseDates.map((date, idx) => ({
          time: date,
          value: Number(rows[idx].profitValue.toFixed(2))
        })),
        options: {
          lineWidth: 2,
          color: '#38bdf8',
          topColor: 'rgba(56, 189, 248, 0.35)',
          bottomColor: 'rgba(56, 189, 248, 0.05)'
        }
      }
    ];
  });

  constructor() {
    this.generateReport();
  }

  addLot(type: LotType): void {
    const model = this.newLot();
    const ticker = model.ticker.trim().toUpperCase();
    if (!ticker) {
      this.loadError.set('Ticker is required.');
      return;
    }
    if (!model.buyDate) {
      this.loadError.set('Choose a buy date.');
      return;
    }
    if (model.shares <= 0 || model.buyPrice <= 0) {
      this.loadError.set('Shares and price must be greater than zero.');
      return;
    }
    const id = `${ticker}-${Date.now()}`;
    const nextLot: Lot = {
      id,
      ticker,
      type,
      buyDate: model.buyDate,
      shares: Number(model.shares),
      buyPrice: Number(model.buyPrice)
    };
    this.lots.update((current) => [...current, nextLot]);
    this.selectedTicker.set(ticker);
    this.newLot.set({
      ...model,
      ticker,
      shares: model.shares,
      buyPrice: model.buyPrice,
      type
    });
    this.loadError.set(null);
    this.generateReport();
  }

  removeLot(id: string): void {
    this.lots.update((current) => current.filter((lot) => lot.id !== id));
    const remainingTickers = this.tickers();
    if (!remainingTickers.includes(this.selectedTicker())) {
      this.selectedTicker.set(remainingTickers[0] ?? '');
    }
    this.generateReport();
  }

  generateReport(): void {
    const ticker = this.selectedTicker().trim().toUpperCase();
    const lots = this.activeLots();
    if (!ticker || lots.length === 0) {
      this.loadError.set('Add at least one lot before generating a report.');
      return;
    }
    const priceSeries = this.buildPriceSeries(30, lots);
    const chartShares = this.sharesForChart();
    const totalShares = lots.reduce((acc, lot) => acc + lot.shares, 0);
    if (chartShares <= 0 || totalShares <= 0) {
      this.loadError.set('Total shares must be positive to generate a chart.');
      return;
    }
    const avgCost = this.averageCost();
    const totalCost = lots.reduce((acc, lot) => acc + lot.buyPrice * lot.shares, 0);
    const scale = chartShares / totalShares;
    const rows: ReportRow[] = priceSeries.map((point) => {
      const perLotProfit =
        this.costMode() === 'AVERAGE_COST'
          ? (point.price - avgCost) * totalShares
          : lots.reduce((acc, lot) => acc + (point.price - lot.buyPrice) * lot.shares, 0);
      const profitValue = perLotProfit * scale;
      const costValue =
        this.costMode() === 'AVERAGE_COST'
          ? avgCost * chartShares
          : totalCost * scale;
      const profitPct = costValue ? profitValue / costValue : 0;
      return {
        date: point.date,
        sellPrice: point.price,
        profitValue,
        profitPct,
        marketValue: point.price * chartShares
      };
    });
    this.reportRows.set(rows);
    this.target.set(null);
    this.loadError.set(null);
  }

  toNumber(value: unknown): number {
    const numeric = typeof value === 'number' ? value : Number(value ?? 0);
    return Number.isNaN(numeric) ? 0 : numeric;
  }

  onChartClick(event: { time: any } | null): void {
    const rows = this.reportRows();
    const time = event?.time;
    if (!time || typeof time !== 'object') {
      return;
    }
    const dateLabel = businessDayToString(time);
    const row = rows.find((r) => r.date === dateLabel);
    if (!row) {
      return;
    }
    const totalShares = this.totalShares();
    if (!totalShares) {
      return;
    }
    const avgCost = this.averageCost();
    const targetPrice = avgCost + row.profitValue / totalShares;
    this.target.set({
      date: row.date,
      profit: Number(row.profitValue.toFixed(2)),
      targetPrice: Number(targetPrice.toFixed(2))
    });
  }

  updateLotForm(patch: Partial<LotForm>): void {
    this.newLot.update((current) => ({ ...current, ...patch }));
  }

  trackByLotId(_: number, lot: Lot): string {
    return lot.id;
  }

  private activeLots(): Lot[] {
    const ticker = this.selectedTicker().trim().toUpperCase();
    return this.lots().filter((lot) => {
      if (lot.ticker !== ticker) return false;
      if (!this.includeHypothetical() && lot.type === 'HYPOTHETICAL') return false;
      return true;
    });
  }

  private buildPriceSeries(days: number, lots: Lot[]): { date: string; price: number }[] {
    const today = new Date();
    const avgCost = this.averageCost();
    const anchor = avgCost || lots.reduce((acc, lot) => acc + lot.buyPrice, 0) / lots.length;
    const series: { date: string; price: number }[] = [];
    let cursor = 0;
    let price = anchor || 100;
    while (series.length < days) {
      const d = new Date(today);
      d.setDate(today.getDate() - cursor);
      cursor += 1;
      const day = d.getDay();
      if (day === 0 || day === 6) {
        continue;
      }
      const noise = Math.sin(series.length / 3) * 0.8;
      price = Math.max(1, price * (1 + 0.0025 + noise / 100));
      series.push({ date: d.toISOString().slice(0, 10), price: Number(price.toFixed(2)) });
    }
    return series.reverse();
  }

  private toDateInput(d: Date): string {
    return d.toISOString().slice(0, 10);
  }
}
