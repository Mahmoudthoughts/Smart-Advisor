import { ApplicationConfig } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { APP_ROUTES } from './app.routes';
import { userBaggageInterceptor } from './http-baggage.interceptor';
import { provideEchartsCore } from 'ngx-echarts';

export const appConfig: ApplicationConfig = {
  providers: [
    provideAnimations(),
    provideHttpClient(withInterceptors([userBaggageInterceptor])),
    provideRouter(APP_ROUTES),
    provideEchartsCore({ echarts: () => import('echarts') })
  ]
};
