import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { createColumnVisibility } from '../shared/column-visibility';

interface OpportunityDay {
  readonly rank: number;
  readonly date: string;
  readonly symbol: string;
  readonly hypoPnl: number;
  readonly dayOpportunity: number;
  readonly deltaVsToday: number;
  readonly narrative: string;
}

interface OpportunityTheme {
  readonly title: string;
  readonly description: string;
  readonly impact: string;
}

@Component({
  selector: 'app-opportunities-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './opportunities.component.html',
  styleUrls: ['./opportunities.component.scss']
})
export class OpportunitiesComponent {
  private readonly columnDefaults = {
    rank: true,
    date: true,
    symbol: true,
    hypoPnl: true,
    dayOpportunity: true,
    deltaVsToday: true,
    narrative: true
  };
  private readonly columnState = createColumnVisibility(
    'smart-advisor.tradv.opportunities.columns',
    this.columnDefaults
  );

  readonly strategies = ['All signals', 'Regret spikes', 'Volume momentum', 'Analyst verified'];
  selectedStrategy = this.strategies[0];
  readonly columns = this.columnState.visibility;
  readonly setColumnVisibility = this.columnState.setVisibility;
  readonly resetColumns = this.columnState.resetVisibility;

  readonly topMissed: OpportunityDay[] = [
    {
      rank: 1,
      date: '2024-03-18',
      symbol: 'PATH',
      hypoPnl: 5120,
      dayOpportunity: 1840,
      deltaVsToday: 1420,
      narrative: 'Close > 17.20 with 1.6× volume and macro easing backdrop.'
    },
    {
      rank: 2,
      date: '2024-02-22',
      symbol: 'TSLA',
      hypoPnl: 4860,
      dayOpportunity: 1520,
      deltaVsToday: 1180,
      narrative: 'Analyst target verified; news sentiment +0.64; rule cooldown cleared.'
    },
    {
      rank: 3,
      date: '2024-01-30',
      symbol: 'NVDA',
      hypoPnl: 4380,
      dayOpportunity: 1280,
      deltaVsToday: 970,
      narrative: 'AI backlog update; ATR breakout with 20D volume multiple at 1.7×.'
    },
    {
      rank: 4,
      date: '2024-01-17',
      symbol: 'LAC',
      hypoPnl: 4120,
      dayOpportunity: 980,
      deltaVsToday: 760,
      narrative: 'Lithium beta reversal; drawdown shrinking 2.4ppts; macro risk-on.'
    }
  ];

  readonly themes: OpportunityTheme[] = [
    {
      title: 'Momentum confirmation',
      description: 'Close + volume + sentiment alignment triggered regret clusters on PATH and NVDA.',
      impact: '+3.6k cumulative missed P&L'
    },
    {
      title: 'Macro catalysts',
      description: 'Regret skew increased into FOMC/CPI windows; protect by laddering exits.',
      impact: '+2.1k incremental if executed'
    },
    {
      title: 'Analyst verification',
      description: 'Signals validated by bullish analyst notes delivered lower drawdowns post-event.',
      impact: 'Drawdown reduced by 1.8ppts'
    }
  ];
}
