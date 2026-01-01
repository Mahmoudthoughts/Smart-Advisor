export const environment = {
  production: false,
  apiBaseUrl: 'http://localhost:8000',
  telemetry: {
    enabled: true,
    serviceName: 'twfrontend',
    exporterUrl: 'http://localhost:4318/v1/traces',
    resourceAttributes: {
      'deployment.environment': 'dev',
      'service.version': '1.0.0'
    },
    propagateTraceHeaderCorsUrls: ['http://localhost:8000']
  }
};
