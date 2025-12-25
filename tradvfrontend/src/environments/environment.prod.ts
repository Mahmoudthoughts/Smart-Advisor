export const environment = {
  production: true,
  apiBaseUrl: '/api',
  telemetry: {
    enabled: true,
    serviceName: 'tradvfrontend',
    exporterUrl: 'http://otel-collector:4318/v1/traces',
    resourceAttributes: {
      'deployment.environment': 'prod',
      'service.version': '1.0.0'
    },
    propagateTraceHeaderCorsUrls: ['http://localhost:8000']
  }
};
