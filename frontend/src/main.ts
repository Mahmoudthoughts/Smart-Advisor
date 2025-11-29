import './telemetry';

import { bootstrapApplication } from '@angular/platform-browser';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { userBaggageInterceptor } from './app/http-baggage.interceptor';
import { provideEchartsCore } from 'ngx-echarts';
import { AppComponent } from './app/app.component';
import { APP_ROUTES } from './app/app.routes';

bootstrapApplication(AppComponent, {
  providers: [
    provideRouter(APP_ROUTES),
    provideAnimations(),
    provideHttpClient(withInterceptors([userBaggageInterceptor])),
    provideEchartsCore({ echarts: () => import('echarts') })
  ]
}).catch((err) => console.error(err));
