// Adds values that differ per environment to app.json without committing them:
// - EAS_PROJECT_ID: from `npx eas init` (needed for builds and push notifications)
// - EXPO_PUBLIC_API_URL: read at runtime by src/constants.ts (defaults to production)
module.exports = ({ config }) => ({
  ...config,
  extra: {
    ...config.extra,
    eas: { ...(config.extra?.eas || {}), ...(process.env.EAS_PROJECT_ID ? { projectId: process.env.EAS_PROJECT_ID } : {}) },
  },
});
