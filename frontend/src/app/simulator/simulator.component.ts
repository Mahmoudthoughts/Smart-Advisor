import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

interface ActionRow {
  readonly id: number;
  type: 'BUY' | 'SELL';
  date: string;
  qtyPct: number;
  price: 'mkt_close' | 'limit';
  limitPrice?: number;
}

interface ResultMetric {
  readonly label: string;
  readonly value: string;
  readonly delta: string;
}

@Component({
  selector: 'app-simulator-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './simulator.component.html',
  styleUrls: ['./simulator.component.scss']
})
export class SimulatorComponent {
  readonly baseTimeline = ['current', 'path_rule_peak', 'macro_shock'];
  selectedTimeline = this.baseTimeline[0];
  readonly actions = signal<ActionRow[]>([
    { id: 1, type: 'SELL', date: '2024-03-20', qtyPct: 50, price: 'mkt_close' },
    { id: 2, type: 'BUY', date: '2024-04-01', qtyPct: 50, price: 'limit', limitPrice: 15.5 }
  ]);

  readonly results: ResultMetric[] = [
    { label: 'P&L delta vs base', value: '+$1,420', delta: '+4.2%' },
    { label: 'Max drawdown delta', value: '-1.8 pts', delta: 'Improved' },
    { label: 'Regret delta (30d)', value: '-$960', delta: 'Lower regret' }
  ];

  addAction(): void {
    const nextId = this.actions().length + 1;
    this.actions.update((rows) => [
      ...rows,
      { id: nextId, type: 'SELL', date: '2024-04-15', qtyPct: 25, price: 'mkt_close' }
    ]);
  }

  updateAction(id: number, partial: Partial<ActionRow>): void {
    this.actions.update((rows) =>
      rows.map((row) => (row.id === id ? { ...row, ...partial } : row))
    );
  }

  removeAction(id: number): void {
    this.actions.update((rows) => rows.filter((row) => row.id !== id));
  }

  trackById(_: number, row: ActionRow): number {
    return row.id;
  }
}
