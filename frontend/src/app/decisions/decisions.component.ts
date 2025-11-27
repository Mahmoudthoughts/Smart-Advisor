import { CommonModule, CurrencyPipe, DatePipe, DecimalPipe, PercentPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import {
  DecisionAction,
  DecisionStatus,
  InvestmentDecision,
  InvestmentDecisionCreatePayload,
  InvestmentDecisionResolvePayload,
  PortfolioDataService
} from '../portfolio-data.service';
import { FormsModule } from '@angular/forms';

interface Option<T> {
  readonly value: T;
  readonly label: string;
}

@Component({
  selector: 'app-decisions',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, CurrencyPipe, DecimalPipe, PercentPipe, DatePipe],
  templateUrl: './decisions.component.html',
  styleUrls: ['./decisions.component.scss']
})
export class DecisionsComponent implements OnInit {
  private readonly data = inject(PortfolioDataService);
  private readonly fb = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);

  readonly isLoading = signal(true);
  readonly isSubmitting = signal(false);
  readonly isResolving = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly createError = signal<string | null>(null);
  readonly resolveError = signal<string | null>(null);

  readonly decisions = signal<InvestmentDecision[]>([]);
  readonly symbolFilter = signal('');
  readonly investorFilter = signal('');
  readonly statusFilter = signal<DecisionStatus | 'ALL'>('ALL');

  readonly selectedDecisionId = signal<number | null>(null);

  readonly actionOptions: Option<DecisionAction>[] = [
    { value: 'BUY_MORE', label: 'Buy more' },
    { value: 'TRIM', label: 'Trim' },
    { value: 'EXIT', label: 'Exit position' },
    { value: 'HOLD', label: 'Hold' }
  ];

  readonly statusOptions: Option<DecisionStatus | 'ALL'>[] = [
    { value: 'ALL', label: 'All statuses' },
    { value: 'OPEN', label: 'Open' },
    { value: 'EXECUTED', label: 'Executed' },
    { value: 'SKIPPED', label: 'Skipped' }
  ];

  readonly createForm = this.fb.nonNullable.group({
    investor: this.fb.nonNullable.control('', [Validators.required]),
    symbol: this.fb.nonNullable.control('', [Validators.required]),
    action: this.fb.nonNullable.control<DecisionAction>('BUY_MORE'),
    planned_quantity: this.fb.control<number | null>(null),
    decision_price: this.fb.control<number | null>(null),
    notes: this.fb.control<string | null>(null)
  });

  readonly resolveForm = this.fb.nonNullable.group({
    status: this.fb.nonNullable.control<DecisionStatus>('EXECUTED'),
    resolved_price: this.fb.control<number | null>(null),
    actual_quantity: this.fb.control<number | null>(null),
    outcome_price: this.fb.control<number | null>(null),
    outcome_notes: this.fb.control<string | null>(null)
  });

  readonly filteredDecisions = computed(() => {
    const symbol = this.symbolFilter().trim().toUpperCase();
    const investor = this.investorFilter().trim().toLowerCase();
    const status = this.statusFilter();

    return this.decisions().filter((item) => {
      if (symbol && !item.symbol.includes(symbol)) return false;
      if (investor && !item.investor.toLowerCase().includes(investor)) return false;
      if (status !== 'ALL' && item.status !== status) return false;
      return true;
    });
  });

  ngOnInit(): void {
    this.applyQueryParams();
    this.loadDecisions();
  }

  loadDecisions(): void {
    this.isLoading.set(true);
    this.loadError.set(null);
    this.data.getDecisions().subscribe({
      next: (items) => {
        this.decisions.set(items);
        this.isLoading.set(false);
      },
      error: () => {
        this.decisions.set([]);
        this.isLoading.set(false);
        this.loadError.set('Unable to load decision history. Please try again.');
      }
    });
  }

  submitDecision(): void {
    this.createError.set(null);
    if (this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }

    const payload: InvestmentDecisionCreatePayload = {
      investor: this.createForm.controls.investor.value.trim(),
      symbol: this.normalizeSymbol(this.createForm.controls.symbol.value),
      action: this.createForm.controls.action.value,
      planned_quantity: this.parseNumber(this.createForm.controls.planned_quantity.value),
      decision_price: this.parseNumber(this.createForm.controls.decision_price.value),
      notes: this.createForm.controls.notes.value?.trim() || null
    };

    this.isSubmitting.set(true);
    this.data.logDecision(payload).subscribe({
      next: (decision) => {
        this.decisions.update((current) => [decision, ...current]);
        this.isSubmitting.set(false);
        this.createForm.reset({
          investor: payload.investor,
          symbol: '',
          action: 'BUY_MORE',
          planned_quantity: null,
          decision_price: null,
          notes: null
        });
      },
      error: (err) => {
        const detail = err?.error?.detail ?? 'Unable to save your decision right now.';
        this.createError.set(typeof detail === 'string' ? detail : 'Unable to save your decision right now.');
        this.isSubmitting.set(false);
      }
    });
  }

  openResolution(decision: InvestmentDecision): void {
    this.selectedDecisionId.set(decision.id);
    this.resolveError.set(null);
    this.resolveForm.setValue({
      status: decision.status === 'OPEN' ? 'EXECUTED' : decision.status,
      resolved_price: decision.resolved_price,
      actual_quantity: decision.actual_quantity ?? decision.planned_quantity,
      outcome_price: decision.outcome_price ?? decision.resolved_price,
      outcome_notes: decision.outcome_notes
    });
  }

  submitResolution(): void {
    const decisionId = this.selectedDecisionId();
    if (!decisionId) {
      return;
    }

    const payload: InvestmentDecisionResolvePayload = {
      status: this.resolveForm.controls.status.value,
      resolved_price: this.parseNumber(this.resolveForm.controls.resolved_price.value),
      actual_quantity: this.parseNumber(this.resolveForm.controls.actual_quantity.value),
      outcome_price: this.parseNumber(this.resolveForm.controls.outcome_price.value),
      outcome_notes: this.resolveForm.controls.outcome_notes.value?.trim() || null
    };

    this.isResolving.set(true);
    this.data.resolveDecision(decisionId, payload).subscribe({
      next: (decision) => {
        this.replaceDecision(decision);
        this.isResolving.set(false);
        this.selectedDecisionId.set(null);
      },
      error: (err) => {
        const detail = err?.error?.detail ?? 'Unable to resolve this decision.';
        this.resolveError.set(typeof detail === 'string' ? detail : 'Unable to resolve this decision.');
        this.isResolving.set(false);
      }
    });
  }

  selectStatus(value: DecisionStatus | 'ALL'): void {
    this.statusFilter.set(value);
  }

  statusClass(status: DecisionStatus): string {
    if (status === 'EXECUTED') return 'chip success';
    if (status === 'SKIPPED') return 'chip muted';
    return 'chip warning';
  }

  trackById(_: number, item: InvestmentDecision): number {
    return item.id;
  }

  private parseNumber(value: number | string | null): number | null {
    if (value === null || value === undefined || value === '') {
      return null;
    }
    const numeric = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  }

  private normalizeSymbol(value: string): string {
    return value.trim().toUpperCase();
  }

  private applyQueryParams(): void {
    const params = this.route.snapshot.queryParamMap;
    const symbolParam = params.get('symbol');
    const investorParam = params.get('investor');
    const statusParam = (params.get('status') ?? '').toUpperCase() as DecisionStatus | '';

    if (symbolParam) {
      const normalized = this.normalizeSymbol(symbolParam);
      this.symbolFilter.set(normalized);
      this.createForm.controls.symbol.setValue(normalized);
    }

    if (investorParam) {
      const trimmed = investorParam.trim();
      this.investorFilter.set(trimmed);
      this.createForm.controls.investor.setValue(trimmed);
    }

    if (statusParam === 'OPEN' || statusParam === 'EXECUTED' || statusParam === 'SKIPPED') {
      this.statusFilter.set(statusParam);
    }
  }

  private replaceDecision(updated: InvestmentDecision): void {
    this.decisions.update((items) =>
      items.map((item) => (item.id === updated.id ? updated : item))
    );
  }
}
