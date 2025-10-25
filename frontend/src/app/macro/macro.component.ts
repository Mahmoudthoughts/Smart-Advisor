import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import type { EChartsOption } from 'echarts';
import { NgxEchartsDirective } from 'ngx-echarts';

interface MacroEventRow {
  readonly date: string;
  readonly label: string;
  readonly importance: 'High' | 'Medium' | 'Low';
  readonly narrative: string;
}

@Component({
  selector: 'app-macro-page',
  standalone: true,
  imports: [CommonModule, NgxEchartsDirective],
  templateUrl: './macro.component.html',
  styleUrls: ['./macro.component.scss']
})
export class MacroComponent {
  readonly yieldOption: EChartsOption = {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 16, top: 32, bottom: 48 },
    xAxis: {
      type: 'category',
      data: ['Jan', 'Feb', 'Mar', 'Apr']
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: '{value}%' }
    },
    series: [
      {
        name: '10Y Treasury yield',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        data: [3.9, 4.1, 4.3, 4.2]
      }
    ]
  };

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
