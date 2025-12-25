import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly errorMessage = signal<string | null>(null);

  constructor() {
    if (this.auth.isAuthenticated()) {
      void this.router.navigate(['/app']);
    }
  }

  readonly credentialsForm = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]]
  });

  readonly requirements = computed(() => [
    'View the missed opportunity dashboard with daily hypothetical liquidation insights.',
    'Track smart advisor narratives, signals, and sentiment overlays in one workspace.',
    'Simulate alternate scenarios and export insights to share with teammates.'
  ]);

  submit(): void {
    if (this.credentialsForm.invalid) {
      this.credentialsForm.markAllAsTouched();
      return;
    }

    this.errorMessage.set(null);
    const { email, password } = this.credentialsForm.getRawValue();
    this.auth.login(email, password).subscribe({
      next: () => void this.router.navigate(['/app']),
      error: (err) => {
        const detail = err?.error?.detail ?? 'Unable to sign in. Check your credentials and try again.';
        this.errorMessage.set(detail);
      }
    });
  }

  get emailControl() {
    return this.credentialsForm.controls.email;
  }

  get passwordControl() {
    return this.credentialsForm.controls.password;
  }
}
