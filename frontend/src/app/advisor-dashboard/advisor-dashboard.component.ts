import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import type { EChartsOption } from 'echarts';
import { NgxEchartsDirective } from 'ngx-echarts';
import { AuthService } from '../auth.service';
import { createColumnVisibility } from '../shared/column-visibility';

interface OpportunityRow {
  readonly rank: number;
  readonly symbol: string;
  readonly missedGain: string;
  readonly driver: string;
}

interface SignalRow {
  readonly label: string;
  readonly symbol: string;
  readonly severity: 'info' | 'watch' | 'action';
  readonly context: string;
}

interface AlertRow {
  readonly symbol: string;
  readonly message: string;
  readonly timestamp: string;
}

interface MacroEvent {
  readonly label: string;
  readonly date: string;
  readonly importance: 'High' | 'Medium' | 'Low';
  readonly takeaway: string;
}

@Component({
  selector: 'app-advisor-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, NgxEchartsDirective, RouterLink],
  templateUrl: './advisor-dashboard.component.html',
  styleUrls: ['./advisor-dashboard.component.scss']
})
export class AdvisorDashboardComponent {
  private readonly auth = inject(AuthService);
  private readonly opportunityColumnDefaults = {
    rank: true,
    symbol: true,
    missedGain: true,
    driver: true
  };
  private readonly opportunityColumnState = createColumnVisibility(
    'smart-advisor.frontend.dashboard.opportunities.columns',
    this.opportunityColumnDefaults
  );

  readonly user = this.auth.user;
  readonly opportunityTableFirst = signal<boolean>(false);
  readonly opportunityColumns = this.opportunityColumnState.visibility;
  readonly setOpportunityColumnVisibility = this.opportunityColumnState.setVisibility;
  readonly resetOpportunityColumns = this.opportunityColumnState.resetVisibility;
  readonly greeting = computed(() => {
    const now = new Date();
    const hour = now.getHours();
    if (hour < 12) {
      return 'Good morning';
    }
    if (hour < 18) {
      return 'Good afternoon';
    }
    return 'Good evening';
  });

  readonly overviewMetrics = [
    {
      label: 'Hypothetical Liquidation P&L',
      value: '+$14,520',
      delta: '+3.8% vs. peak',
      accent: 'positive'
    },
    {
      label: 'Regret Today',
      value: '$2,140',
      delta: 'Top opportunity: PATH (Mar 18)',
      accent: 'caution'
    },
    {
      label: 'Signals Active',
      value: '4',
      delta: '2 action, 1 watch, 1 info',
      accent: 'neutral'
    },
    {
      label: 'Narratives Generated',
      value: '3',
      delta: 'Daily, Weekly, Macro pulse',
      accent: 'neutral'
    }
  ];

  readonly liquidationChart: EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Hypo P&L', 'Unrealized P&L', 'Price'] },
    grid: { left: 40, right: 16, top: 40, bottom: 40 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Mon', 'Tue']
    },
    yAxis: [
      {
        type: 'value',
        axisLabel: { formatter: '${value}k' }
      },
      {
        type: 'value',
        axisLabel: { formatter: '${value}' },
        position: 'right'
      }
    ],
    series: [
      {
        name: 'Hypo P&L',
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.15 },
        data: [9.2, 9.6, 10.1, 10.8, 11.4, 11.2, 11.8]
      },
      {
        name: 'Unrealized P&L',
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.1 },
        data: [6.1, 6.4, 6.8, 7.2, 7.5, 7.4, 7.8]
      },
      {
        name: 'Price',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        lineStyle: { width: 2, type: 'dashed' },
        data: [14.2, 14.6, 15, 15.4, 15.9, 15.5, 16.1]
      }
    ]
  };

  readonly opportunityChart: EChartsOption = {
    tooltip: { trigger: 'item', formatter: '{b}: ${c}k' },
    xAxis: {
      type: 'category',
      data: ['PATH', 'TSLA', 'NVDA', 'LAC', 'MSFT']
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: '${value}k' }
    },
    series: [
      {
        type: 'bar',
        data: [4.8, 3.6, 2.9, 2.2, 1.8],
        itemStyle: {
          color: '#38bdf8',
          borderRadius: [12, 12, 0, 0]
        }
      }
    ]
  };

  readonly opportunities: OpportunityRow[] = [
    { rank: 1, symbol: 'PATH', missedGain: '$4.8k', driver: 'Sell signal + macro easing' },
    { rank: 2, symbol: 'TSLA', missedGain: '$3.6k', driver: 'Verified analyst upgrade' },
    { rank: 3, symbol: 'NVDA', missedGain: '$2.9k', driver: 'Volume 1.8× 20D + AI backlog' },
    { rank: 4, symbol: 'LAC', missedGain: '$2.2k', driver: 'Lithium beta shock normalized' },
    { rank: 5, symbol: 'MSFT', missedGain: '$1.8k', driver: 'Drawdown reversal at 50DMA' }
  ];

  readonly signals: SignalRow[] = [
    {
      label: 'Momentum breach confirmed',
      symbol: 'PATH',
      severity: 'action',
      context: 'Close > 17.20 with 1.6× volume and sentiment alignment.'
    },
    {
      label: 'Analyst insight verified',
      symbol: 'TSLA',
      severity: 'watch',
      context: 'Price momentum and news sentiment agree with $600 target.'
    },
    {
      label: 'Macro proximity alert',
      symbol: 'QQQ',
      severity: 'info',
      context: 'CPI release in 2 days; implied regret delta +1.2%.'
    },
    {
      label: 'Predictor nudge',
      symbol: 'NVDA',
      severity: 'action',
      context: '30-day peak retake probability 68%; partial trimming advised.'
    }
  ];

  readonly alerts: AlertRow[] = [
    {
      symbol: 'LAC',
      message: 'Drawdown explanation: post-earnings guidance. Historical recovery 9–14 days.',
      timestamp: 'Today · 10:12'
    },
    {
      symbol: 'PATH',
      message: 'New peak alert: Hypo P&L set new 30D high. Consider scaling exit plan.',
      timestamp: 'Yesterday · 15:41'
    },
    {
      symbol: 'TSLA',
      message: 'Signal triggered: Verified analyst insight. Aligning with sentiment momentum.',
      timestamp: 'Yesterday · 09:05'
    }
  ];

  readonly macroEvents: MacroEvent[] = [
    {
      label: 'FOMC Rate Decision',
      date: 'Mar 27 · 18:00',
      importance: 'High',
      takeaway: 'Probability of pause 76%; watch beta adjustments for growth names.'
    },
    {
      label: 'CPI Release',
      date: 'Apr 10 · 16:30',
      importance: 'High',
      takeaway: 'Scenario simulator suggests +1.4% regret delta if headline surprises +50bps.'
    },
    {
      label: 'ISM Manufacturing',
      date: 'Apr 01 · 17:00',
      importance: 'Medium',
      takeaway: 'Correlations show PATH sensitivity at 0.64; monitor volumes.'
    }
  ];
}
