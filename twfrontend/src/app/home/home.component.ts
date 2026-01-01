import { CommonModule } from '@angular/common';
import { Component, computed, signal } from '@angular/core';
import { ChartPanelComponent } from '../shared/chart-panel/chart-panel.component';
import { MarketDataService } from '../services/market-data.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, ChartPanelComponent],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent {
  readonly symbol = signal('AAPL');
  readonly timeframes = ['1W', '1M', '3M', '6M', '1Y'];
  readonly selectedTimeframe = signal('3M');
  readonly candles = signal(this.marketData.getSampleCandles('3M'));

  readonly lastClose = computed(() => {
    const data = this.candles();
    return data.length ? data[data.length - 1].close : 0;
  });

  readonly delta = computed(() => {
    const data = this.candles();
    if (data.length < 2) {
      return 0;
    }
    const last = data[data.length - 1].close;
    const prev = data[data.length - 2].close;
    return last - prev;
  });

  constructor(private readonly marketData: MarketDataService) {}

  setTimeframe(range: string): void {
    this.selectedTimeframe.set(range);
    this.candles.set(this.marketData.getSampleCandles(range));
  }
}
