// Single place for the backend location — change this if your Flask server runs elsewhere.
const API_HOST = window.location.hostname || "127.0.0.1";
const API_BASE_URL = `http://${API_HOST}:5000`;

async function apiRequest(path, options = {}) {
  try {
    const isCustomer = path.startsWith("/api/chat") || path.startsWith("/api/reviews");
    const storeKey = isCustomer ? "netassist_customer" : "netassist_admin";
    const store = JSON.parse(localStorage.getItem(storeKey) || "null");
    const res = await fetch(API_BASE_URL + path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(store && store.token ? { Authorization: "Bearer " + store.token } : {}),
        ...(options.headers || {}),
      },
    });
    let data = null;
    try { data = await res.json(); } catch (e) { /* no/invalid JSON body */ }
    if (res.status === 401 && !path.startsWith("/api/auth")) {
      // Session missing/expired: send the user to the matching login page.
      localStorage.removeItem(storeKey);
      window.location.href = isCustomer ? "customer-login.html" : "admin-login.html";
    }
    if (!res.ok) {
      const msg = (data && (data.error || data.message)) || `Request failed (${res.status})`;
      return { ok: false, status: res.status, error: msg, data };
    }
    return { ok: true, status: res.status, data };
  } catch (err) {
    return {
      ok: false,
      status: 0,
      error: `Could not reach the backend at ${API_BASE_URL}. Is your Flask server running?`,
      data: null,
    };
  }
}

const NetAssistAPI = {
  startChat: (accountNumber, complaintType) =>
    apiRequest("/api/chat/start", {
      method: "POST",
      body: JSON.stringify({ account_number: accountNumber, complaint_type: complaintType }),
    }),
  sendMessage: (sessionId, content) =>
    apiRequest(`/api/chat/${sessionId}/message`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
  streamMessage: async (sessionId, content, onChunk) => {
    try {
      const store = JSON.parse(localStorage.getItem("netassist_customer") || "null");
      const res = await fetch(`${API_BASE_URL}/api/chat/${sessionId}/message/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(store && store.token ? { Authorization: "Bearer " + store.token } : {}),
        },
        body: JSON.stringify({ content }),
      });
      if (!res.ok) {
        let data = null;
        try { data = await res.json(); } catch (_) {}
        return { ok: false, status: res.status, error: (data && data.error) || `Request failed (${res.status})`, data };
      }
      if (!res.body) return { ok: false, status: 0, error: "Streaming is not available in this browser.", data: null };
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let text = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        if (chunk) { text += chunk; if (onChunk) onChunk(chunk, text); }
      }
      const tail = decoder.decode();
      if (tail) { text += tail; if (onChunk) onChunk(tail, text); }
      return { ok: true, status: res.status, data: { reply: text } };
    } catch (err) {
      return { ok: false, status: 0, error: `Could not reach the backend at ${API_BASE_URL}. Is your Flask server running?`, data: null };
    }
  },
  getChatStatus: (sessionId) => apiRequest(`/api/chat/${sessionId}/status`),
    confirmClosure: (sessionId, resolved) =>
    apiRequest(`/api/chat/${sessionId}/confirm-closure`, {
      method: "POST",
      body: JSON.stringify({ resolved }),
    }),
  getChatHistory: () => apiRequest("/api/chat/history"),
  submitReview: (accountNumber, reviewText) =>
    apiRequest("/api/reviews/", {
      method: "POST",
      body: JSON.stringify({ account_number: accountNumber, review_text: reviewText }),
    }),
  getEscalations: (status = "open") => apiRequest(`/api/escalations/?status=${encodeURIComponent(status)}`),
  getAdminAnalytics: () => apiRequest("/api/admin/analytics"),
  getEscalation: (id) => apiRequest(`/api/escalations/${id}`),
  summarizeEscalation: (id) => apiRequest(`/api/escalations/${id}/summarize`, {method: 'POST' }), 
  updateEscalationStatus: (id, status) =>
    apiRequest(`/api/escalations/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  getAdminStats: () => apiRequest("/api/admin/stats"),
  askAdminAI: (question) =>
    apiRequest("/api/admin/ai", { method: "POST", body: JSON.stringify({ question }) }),
  previewBatch: (filters) =>
    apiRequest("/api/batch/preview", { method: "POST", body: JSON.stringify(filters) }),
  processBatch: (payload) =>
    apiRequest("/api/batch/process", { method: "POST", body: JSON.stringify(payload) }),
  getBatchHistory: () => apiRequest("/api/batch/history"),
  customerLogin: (identifier, pin, loginType = "email") =>
  apiRequest("/api/auth/customer/login", {
    method: "POST",
    body: JSON.stringify(
      loginType === "account"
        ? { account_number: identifier, pin }
        : { email: identifier, pin }
    ),
  }),
  customerRegister: (payload) =>
    apiRequest("/api/auth/customer/register", { method: "POST", body: JSON.stringify(payload) }),
  adminLogin: (username, password) =>
    apiRequest("/api/auth/admin/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  listCustomers: (status = "all") => apiRequest(`/api/customers/?status=${encodeURIComponent(status)}`),
  createCustomer: (payload) => apiRequest("/api/customers/", { method: "POST", body: JSON.stringify(payload) }),
  approveCustomer: (id) => apiRequest(`/api/customers/${id}/approve`, { method: "POST" }),
  disableCustomer: (id) => apiRequest(`/api/customers/${id}/disable`, { method: "POST" }),
  importCustomers: (csv) => apiRequest("/api/customers/import", { method: "POST", body: JSON.stringify({ csv }) }),
  getNotifications: () => apiRequest("/api/escalations/notifications"),
  acknowledgeEscalation: (id) => apiRequest(`/api/escalations/${id}/acknowledge`, { method: "POST" }),
  replyToEscalation: (id, content) => apiRequest(`/api/escalations/${id}/reply`, { method: "POST", body: JSON.stringify({ content }) }),
  getPublicReviews: () => apiRequest("/api/reviews/public"),
};
