# Smart Advisor Frontend

This Angular workspace provides the web experience for the Smart Advisor platform. The starter shell renders a landing view that can be extended with dashboards, missed-opportunity analytics, and alerting interfaces backed by the Python service in `../backend`.

## Getting Started

```bash
cd frontend
npm install
npm start
```

The development server listens on `http://localhost:4200/` by default. Update the `environment` files to point at the deployed backend API gateway.

## Building

```bash
npm run build
```

Production builds emit assets under `dist/smart-advisor`.
