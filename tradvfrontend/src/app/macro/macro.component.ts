import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { mapLineSeries } from '../shared/chart-utils';
import { TvChartComponent, TvSeries } from '../shared/tv-chart/tv-chart.component';

interface MacroEventRow {
  readonly date: string;
  readonly label: string;
  readonly importance: 'High' | 'Medium' | 'Low';
  readonly narrative: string;
}

@Component({
  selector: 'app-macro-page',
  standalone: true,
  imports: [CommonModule, TvChartComponent],
  templateUrl: './macro.component.html',
  styleUrls: ['./macro.component.scss']
})
export class MacroComponent {
  readonly yieldSeries: TvSeries[] = [
    {
      type: 'line',
      data: mapLineSeries([3.9, 4.1, 4.3, 4.2]),
      options: {
        lineWidth: 2,
        color: '#38bdf8'
      }
    }
  ];

  readonly events: MacroEventRow[] = [
    {
      date: '2024-03-27 18:00',
      label: 'FOMC Rate Decision',
      importance: 'High',
      narrative: 'Market pricing 76% probability of pause; monitor growth beta sensitivity.'
    },
    {
      date: '2024-04-10 16:30',
      label: 'CPI Release',
      importance: 'High',
      narrative: 'Scenario simulator indicates +1.4% regret delta if headline surprise +50bps.'
    },
    {
      date: '2024-04-01 17:00',
      label: 'ISM Manufacturing',
      importance: 'Medium',
      narrative: 'Rolling beta vs. manufacturing PMI rising; keep stop adjustments tight.'
    }
  ];
}
