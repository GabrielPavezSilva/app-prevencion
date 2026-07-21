// Base API client configuration
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

class ApiClient {
  constructor(baseURL = BASE_URL) {
    this.baseURL = baseURL;
    this.headers = {
      "Content-Type": "application/json",
    };
    // Indica si enviar cookies en cada request (true para el backend principal)
    this._credentials = "include";
  }

  setCredentials(value) {
    this._credentials = value;
  }

  // Mantenido por compatibilidad — ya no se usa con cookies httpOnly
  setAuthToken(token) {
    if (token) {
      this.headers["Authorization"] = `Bearer ${token}`;
    } else {
      delete this.headers["Authorization"];
    }
  }

  // Handle response
  async handleResponse(response, customConfig = {}) {
    if (!response.ok) {
      const isJson = response.headers.get("content-type")?.includes("application/json");
      const error = isJson ? await response.json().catch(() => ({ message: "An error occurred" })) : { message: await response.text() };
      throw new Error(
        error.detail || error.message || `HTTP Error: ${response.status}`,
      );
    }

    if (customConfig.responseType === 'blob') {
      return response.blob();
    }

    return response.json();
  }

  // GET request
  async get(endpoint, customConfig = {}) {
    try {
      const requestHeaders = { ...this.headers, ...(customConfig.headers || {}) };
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        method: "GET",
        headers: requestHeaders,
        credentials: this._credentials,
        ...customConfig
      });
      return this.handleResponse(response, customConfig);
    } catch (error) {
      console.error("GET Error:", error);
      throw error;
    }
  }

  // POST request
  async post(endpoint, data, customConfig = {}) {
    try {
      const isFormData = data instanceof FormData;
      const requestHeaders = { ...this.headers, ...(customConfig.headers || {}) };

      if (isFormData) {
        delete requestHeaders["Content-Type"];
      } else if (data === undefined || data === null) {
        delete requestHeaders["Content-Type"];
      }

      const response = await fetch(`${this.baseURL}${endpoint}`, {
        method: "POST",
        headers: requestHeaders,
        credentials: this._credentials,
        body: isFormData ? data : (data !== undefined && data !== null ? JSON.stringify(data) : undefined),
        ...customConfig
      });
      return this.handleResponse(response, customConfig);
    } catch (error) {
      console.error("POST Error:", error);
      throw error;
    }
  }

  // PUT request
  async put(endpoint, data, customConfig = {}) {
    try {
      const isFormData = data instanceof FormData;
      const requestHeaders = { ...this.headers, ...(customConfig.headers || {}) };

      if (isFormData) {
        delete requestHeaders["Content-Type"];
      }

      const response = await fetch(`${this.baseURL}${endpoint}`, {
        method: "PUT",
        headers: requestHeaders,
        credentials: this._credentials,
        body: isFormData ? data : JSON.stringify(data),
        ...customConfig
      });
      return this.handleResponse(response, customConfig);
    } catch (error) {
      console.error("PUT Error:", error);
      throw error;
    }
  }

  // PATCH request
  async patch(endpoint, data, customConfig = {}) {
    try {
      const isFormData = data instanceof FormData;
      const requestHeaders = { ...this.headers, ...(customConfig.headers || {}) };

      if (isFormData) {
        delete requestHeaders["Content-Type"];
      }

      const response = await fetch(`${this.baseURL}${endpoint}`, {
        method: "PATCH",
        headers: requestHeaders,
        credentials: this._credentials,
        body: isFormData ? data : JSON.stringify(data),
        ...customConfig
      });
      return this.handleResponse(response, customConfig);
    } catch (error) {
      console.error("PATCH Error:", error);
      throw error;
    }
  }

  // DELETE request
  async delete(endpoint, customConfig = {}) {
    try {
      const requestHeaders = { ...this.headers, ...(customConfig.headers || {}) };
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        method: "DELETE",
        headers: requestHeaders,
        credentials: this._credentials,
        ...customConfig
      });
      return this.handleResponse(response, customConfig);
    } catch (error) {
      console.error("DELETE Error:", error);
      throw error;
    }
  }
}

export const apiClient = new ApiClient();
