import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';

interface AlertRow {
  readonly timestamp: string;
  readonly symbol: string;
  readonly type: 'Drawdown++' | 'Signal Trigger' | 'Macro Proximity' | 'New Peak';
  readonly explanation: string;
  readonly analogue: string;
}

interface NarrativeRow {
  readonly title: string;
  readonly timeframe: string;
  readonly highlights: string[];
}

@Component({
  selector: 'app-alerts-page',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './alerts.component.html',
  styleUrls: ['./alerts.component.scss']
})
export class AlertsComponent {
  readonly alerts: AlertRow[] = [
    {
      timestamp: '2024-03-18 · 10:12 Asia/Dubai',
      symbol: 'LAC',
      type: 'Drawdown++',
      explanation: 'Drawdown -6.8% from peak; cause: post-earnings guidance; recovery window 9–14 days.',
      analogue: 'Analogue: 2022-08-14 to 2022-08-28'
    },
    {
      timestamp: '2024-03-17 · 09:05 Asia/Dubai',
      symbol: 'TSLA',
      type: 'Signal Trigger',
      explanation: 'Analyst verification triggered; explanation: sentiment + momentum alignment with $600 target.',
      analogue: 'Analogue: 2023-06-11 breakout'
    },
    {
      timestamp: '2024-03-16 · 15:41 Asia/Dubai',
      symbol: 'PATH',
      type: 'New Peak',
      explanation: 'Hypo P&L set 30D high; suggested action: stage trim ladder 20% each + trailing stop.',
      analogue: 'Analogue: 2024-02-18 partial exit'
    }
  ];

  readonly narratives: NarrativeRow[] = [
    {
      title: 'Daily narrative',
      timeframe: '2024-03-18',
      highlights: [
        'Leaders: PATH +2.1% unrealized; Laggards: LAC -3.6% weighed.',
        'Signals: PATH momentum breach verified; NVDA predictor nudge triggered.',
        'Macro: FOMC pause odds 76%, watch growth beta.'
      ]
    },
    {
      title: 'Weekly pulse',
      timeframe: 'Week 2024-W11',
      highlights: [
        'Regret intensity peaked mid-week on PATH; plan incremental exits.',
        'Analyst upgrades on TSLA validated; maintain watch on volume multiple.',
        'Macro overlays: CPI + FOMC cluster—hedges recommended.'
      ]
    }
  ];
}
