import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';

interface ForecastScenario {
  readonly horizon: string;
  readonly probability: number;
  readonly regretDelta: string;
  readonly drivers: string[];
}

interface ForecastInsight {
  readonly title: string;
  readonly summary: string;
  readonly action: string;
}

@Component({
  selector: 'app-forecast-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './forecast.component.html',
  styleUrls: ['./forecast.component.scss']
})
export class ForecastComponent {
  readonly symbols = ['PATH', 'TSLA', 'NVDA'];
  selectedSymbol = this.symbols[0];
  asOfDate = '2024-03-18';

  readonly scenarios: ForecastScenario[] = [
    {
      horizon: 'Retake peak (30d)',
      probability: 0.68,
      regretDelta: '-$1.2k vs sell today',
      drivers: ['Momentum +', 'Sentiment +', 'Macro neutral']
    },
    {
      horizon: 'Drawdown extends (30d)',
      probability: 0.22,
      regretDelta: '+$0.8k vs sell today',
      drivers: ['Volatility cluster', 'Macro risk events']
    },
    {
      horizon: 'Range-bound (30d)',
      probability: 0.1,
      regretDelta: '-$0.2k vs sell today',
      drivers: ['Lack of catalysts']
    }
  ];

  readonly insights: ForecastInsight[] = [
    {
      title: 'Base case still favors partial hold',
      summary: 'Probability-weighted regret skews negative; maintain trailing stop to protect gains.',
      action: 'Hold 60% position; evaluate exit triggers on rule alignment.'
    },
    {
      title: 'Macro risk hedges recommended',
      summary: 'Treasury yield climb can compress multiples; consider protective puts on correlated ETFs.',
      action: 'Allocate 1.5% to hedges near CPI release.'
    },
    {
      title: 'Narrative momentum',
      summary: 'News sentiment positive three days running; align with analyst verification for upgrades.',
      action: 'Engage auto-alerts for conflicting sentiment.'
    }
  ];
}
