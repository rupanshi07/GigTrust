// Same origin when served by the API (/app), local backend when run on port 5500
window.GIGTRUST_CONFIG = {
  API_BASE_URL: (location.port === "5500") ? "http://127.0.0.1:8000" : location.origin
};
