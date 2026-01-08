
export {};
declare global {
    const CSRF_TOKEN: string;
    const MOKKAPI_ADMIN_PREFIX: string;
    interface Window {
      APP_CONFIG: {
        apiPrefix: string;
      };
    }
}