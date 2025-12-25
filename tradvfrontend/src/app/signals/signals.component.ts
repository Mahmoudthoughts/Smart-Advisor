import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

interface SignalDefinition {
  readonly id: string;
  readonly label: string;
  readonly description: string;
  readonly cooldownDays: number;
  readonly status: 'active' | 'draft';
}

interface SignalEventRow {
  readonly date: string;
  readonly symbol: string;
  readonly ruleId: string;
  readonly signalType: string;
  readonly severity: 'info' | 'watch' | 'action';
  readonly context: string;
}

type RuleForm = {
  symbol: string;
  condition: string;
  cooldown: number;
  severity: 'info' | 'watch' | 'action';
};

@Component({
  selector: 'app-signals-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './signals.component.html',
  styleUrls: ['./signals.component.scss']
})
export class SignalsComponent {
  readonly rules: SignalDefinition[] = [
    {
      id: 'path_breakout',
      label: 'PATH momentum breakout',
      description: 'Close > 17.20 AND volume >= 1.5× 20D average',
      cooldownDays: 2,
      status: 'active'
    },
    {
      id: 'macro_guard',
      label: 'Macro proximity guard',
      description: 'Trigger when CPI/FOMC within 3 days and drawdown > 5%',
      cooldownDays: 1,
      status: 'active'
    },
    {
      id: 'analyst_verify',
      label: 'Analyst verification',
      description: 'Analyst rating upgrade confirmed by positive sentiment + momentum',
      cooldownDays: 5,
      status: 'draft'
    }
  ];

  readonly events: SignalEventRow[] = [
    {
      date: '2024-03-18',
      symbol: 'PATH',
      ruleId: 'path_breakout',
      signalType: 'Momentum breach confirmed',
      severity: 'action',
      context: 'Close 17.68 > trigger; volume 1.6× 20D; sentiment +0.52.'
    },
    {
      date: '2024-03-17',
      symbol: 'TSLA',
      ruleId: 'analyst_verify',
      signalType: 'Analyst insight verified',
      severity: 'watch',
      context: 'Price > EMA20, sentiment +0.64, target $600 aligns.'
    },
    {
      date: '2024-03-15',
      symbol: 'QQQ',
      ruleId: 'macro_guard',
      signalType: 'Macro proximity alert',
      severity: 'info',
      context: 'CPI in 2 days; drawdown -4.1%; hedge recommended.'
    }
  ];

  readonly ruleForm = signal<RuleForm>({
    symbol: 'PATH',
    condition: 'close > 17.20 AND volume >= 1.5x20d',
    cooldown: 2,
    severity: 'action'
  });

  updateForm<K extends keyof RuleForm>(key: K, value: RuleForm[K]): void {
    this.ruleForm.update((current) => ({ ...current, [key]: value }));
  }
}
