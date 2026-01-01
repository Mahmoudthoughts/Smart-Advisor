import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import {
  AdminService,
  AdminUser,
  AdminUserCreate,
  StockListProviderConfig,
  StockListProviderUpsert
} from '../admin.service';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, DatePipe],
  templateUrl: './admin.component.html',
  styleUrls: ['./admin.component.scss']
})
export class AdminComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly formBuilder = inject(FormBuilder);

  readonly users = signal<AdminUser[]>([]);
  readonly providers = signal<StockListProviderConfig[]>([]);
  readonly userStatus = signal<string | null>(null);
  readonly userError = signal<string | null>(null);
  readonly providerStatus = signal<string | null>(null);
  readonly providerError = signal<string | null>(null);
  readonly isLoadingUsers = signal<boolean>(true);
  readonly isLoadingProviders = signal<boolean>(true);
  readonly passwordDrafts = signal<Record<string, string>>({});
  readonly providerDrafts = signal<Record<string, StockListProviderUpsert | undefined>>({});

  readonly userForm = this.formBuilder.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    role: ['user', [Validators.required]]
  });

  readonly providerForm = this.formBuilder.group({
    provider: ['', [Validators.required, Validators.minLength(2)]],
    display_name: ['', [Validators.required, Validators.minLength(2)]],
    api_key: [''],
    base_url: [''],
    is_active: [true],
    is_default: [false]
  });

  ngOnInit(): void {
    this.loadUsers();
    this.loadProviders();
  }

  loadUsers(): void {
    this.isLoadingUsers.set(true);
    this.userError.set(null);
    this.adminService.listUsers().subscribe({
      next: (users) => {
        this.users.set(users);
        this.isLoadingUsers.set(false);
        this.passwordDrafts.set({});
      },
      error: () => {
        this.users.set([]);
        this.isLoadingUsers.set(false);
        this.userError.set('Unable to load users right now.');
      }
    });
  }

  loadProviders(): void {
    this.isLoadingProviders.set(true);
    this.providerError.set(null);
    this.adminService.listProviders().subscribe({
      next: (providers) => {
        this.providers.set(providers);
        this.isLoadingProviders.set(false);
        this.syncProviderDrafts(providers);
      },
      error: () => {
        this.providers.set([]);
        this.isLoadingProviders.set(false);
        this.providerError.set('Unable to load provider settings.');
      }
    });
  }

  submitNewUser(): void {
    this.userStatus.set(null);
    this.userError.set(null);
    if (this.userForm.invalid) {
      this.userForm.markAllAsTouched();
      return;
    }
    const payload = this.userForm.getRawValue() as AdminUserCreate;
    this.adminService.createUser(payload).subscribe({
      next: (user) => {
        this.users.update((items) => [...items, user]);
        this.userStatus.set(`Created ${user.name} (${user.email}).`);
        this.userForm.reset({ role: 'user' });
      },
      error: (err) => {
        const detail = err?.error?.detail ?? 'Unable to create the user.';
        this.userError.set(typeof detail === 'string' ? detail : 'Unable to create the user.');
      }
    });
  }

  changeUserRole(user: AdminUser, role: string): void {
    if (!role || role === user.role) return;
    this.userStatus.set(null);
    this.userError.set(null);
    this.adminService.updateUser(user.id, { role }).subscribe({
      next: (updated) => {
        this.users.update((items) => items.map((item) => (item.id === updated.id ? updated : item)));
        this.userStatus.set(`Updated role for ${updated.email} to ${updated.role}.`);
      },
      error: () => {
        this.userError.set('Unable to update the user role right now.');
      }
    });
  }

  setPasswordDraft(userId: string, value: string): void {
    this.passwordDrafts.update((drafts) => ({ ...drafts, [userId]: value }));
  }

  resetPassword(user: AdminUser): void {
    const draft = this.passwordDrafts()[user.id];
    if (!draft || draft.trim().length < 8) {
      this.userError.set('Passwords must be at least 8 characters.');
      return;
    }
    this.userStatus.set(null);
    this.userError.set(null);
    this.adminService.updateUser(user.id, { password: draft }).subscribe({
      next: (updated) => {
        this.userStatus.set(`Reset password for ${updated.email}.`);
        this.passwordDrafts.update((drafts) => ({ ...drafts, [user.id]: '' }));
      },
      error: () => {
        this.userError.set('Unable to reset the password right now.');
      }
    });
  }

  deleteUser(user: AdminUser): void {
    this.userStatus.set(null);
    this.userError.set(null);
    this.adminService.deleteUser(user.id).subscribe({
      next: () => {
        this.users.update((items) => items.filter((item) => item.id !== user.id));
        this.userStatus.set(`Deleted ${user.email}.`);
      },
      error: () => {
        this.userError.set('Unable to delete the user right now.');
      }
    });
  }

  submitNewProvider(): void {
    this.providerStatus.set(null);
    this.providerError.set(null);
    if (this.providerForm.invalid) {
      this.providerForm.markAllAsTouched();
      return;
    }
    const payload = this.providerForm.getRawValue();
    this.adminService.createProvider(payload as StockListProviderUpsert).subscribe({
      next: (provider) => {
        this.providers.update((items) => [...items, provider]);
        this.syncProviderDrafts(this.providers());
        this.providerStatus.set(`Created provider ${provider.display_name}.`);
        this.providerForm.reset({ is_active: true, is_default: false });
      },
      error: (err) => {
        const detail = err?.error?.detail ?? 'Unable to create the provider.';
        this.providerError.set(typeof detail === 'string' ? detail : 'Unable to create the provider.');
      }
    });
  }

  editProviderField(providerId: string, field: keyof StockListProviderUpsert, value: string | boolean): void {
    this.providerDrafts.update((drafts) => {
      const current = drafts[providerId] ?? this.buildProviderDraft(this.providers().find((p) => p.id === providerId));
      if (!current) return drafts;
      return { ...drafts, [providerId]: { ...current, [field]: value } };
    });
  }

  saveProvider(providerId: string): void {
    const draft = this.providerDrafts()[providerId];
    if (!draft) return;
    this.providerStatus.set(null);
    this.providerError.set(null);
    this.adminService.updateProvider(providerId, draft).subscribe({
      next: (provider) => {
        this.providers.update((items) => items.map((item) => (item.id === provider.id ? provider : item)));
        this.syncProviderDrafts(this.providers());
        this.providerStatus.set(`Updated ${provider.display_name}.`);
      },
      error: () => {
        this.providerError.set('Unable to update the provider right now.');
      }
    });
  }

  trackById(_: number, item: { id: string }): string {
    return item.id;
  }

  private buildProviderDraft(provider?: StockListProviderConfig): StockListProviderUpsert | undefined {
    if (!provider) return undefined;
    return {
      provider: provider.provider,
      display_name: provider.display_name,
      api_key: provider.api_key,
      base_url: provider.base_url,
      is_active: provider.is_active,
      is_default: provider.is_default
    };
  }

  private syncProviderDrafts(providers: StockListProviderConfig[]): void {
    const drafts: Record<string, StockListProviderUpsert | undefined> = {};
    providers.forEach((provider) => {
      drafts[provider.id] = this.buildProviderDraft(provider)!;
    });
    this.providerDrafts.set(drafts);
  }
}
