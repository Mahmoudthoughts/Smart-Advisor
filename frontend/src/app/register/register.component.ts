import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss']
})
export class RegisterComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly errorMessage = signal<string | null>(null);

  readonly registerForm = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    confirmPassword: ['', [Validators.required, Validators.minLength(8)]]
  });

  submit(): void {
    if (this.registerForm.invalid || !this.passwordsMatch()) {
      this.registerForm.markAllAsTouched();
      if (!this.passwordsMatch()) {
        this.errorMessage.set('Passwords must match.');
      }
      return;
    }

    this.errorMessage.set(null);
    const { name, email, password } = this.registerForm.getRawValue();
    this.auth.register(name, email, password).subscribe({
      next: () => void this.router.navigate(['/app']),
      error: (err) => {
        const detail = err?.error?.detail ?? 'Unable to create the account. Please try again.';
        this.errorMessage.set(detail);
      }
    });
  }

  passwordsMatch(): boolean {
    const { password, confirmPassword } = this.registerForm.getRawValue();
    return password === confirmPassword;
  }

  get nameControl() {
    return this.registerForm.controls.name;
  }

  get emailControl() {
    return this.registerForm.controls.email;
  }

  get passwordControl() {
    return this.registerForm.controls.password;
  }

  get confirmPasswordControl() {
    return this.registerForm.controls.confirmPassword;
  }
}
