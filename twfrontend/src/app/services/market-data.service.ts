import { Injectable } from '@angular/core';
import { BusinessDay, CandlestickData } from 'lightweight-charts';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class MarketDataService {
  private readonly apiBaseUrl = environment.apiBaseUrl;

  getSampleCandles(range: string = '3M'): CandlestickData[] {
    const candles: CandlestickData[] = [];
    const count = this.resolveSampleCount(range);
    let base = 176;

    for (let i = 0; i < count; i += 1) {
      const date = new Date(Date.UTC(2024, 0, 2 + i));
      const swing = Math.sin(i / 4) * 2.2;
      const open = base + swing;
      const close = open + (i % 2 === 0 ? 1.4 : -1.1);
      const high = Math.max(open, close) + 1.8;
      const low = Math.min(open, close) - 1.5;
      base += 0.45;

      candles.push({
        time: this.toBusinessDay(date),
        open: this.round(open),
        high: this.round(high),
        low: this.round(low),
        close: this.round(close)
      });
    }

    return candles;
  }

  get baseUrl(): string {
    return this.apiBaseUrl;
  }

  private toBusinessDay(date: Date): BusinessDay {
    return {
      year: date.getUTCFullYear(),
      month: date.getUTCMonth() + 1,
      day: date.getUTCDate()
    };
  }

  private round(value: number): number {
    return Math.round(value * 100) / 100;
  }

  private resolveSampleCount(range: string): number {
    switch (range) {
      case '1W':
        return 7;
      case '1M':
        return 22;
      case '6M':
        return 120;
      case '1Y':
        return 240;
      case '3M':
      default:
        return 60;
    }
  }
}
