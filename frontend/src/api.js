/**
 * DermaSense API Client.
 * Connects React frontend to FastAPI backend using configured API base URL.
 * Handles network failures, timeouts, and structured error responses.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

/**
 * Sends image to /api/predict.
 * @param {File|Blob} file - Uploaded skin photo
 * @returns {Promise<Object>} Formatted prediction object
 */
export async function predictSkinCondition(file) {
  const formData = new FormData();
  formData.append('file', file, file.name || 'skin_upload.jpg');

  try {
    const response = await fetch(`${API_BASE}/api/predict`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorDetail = `Request failed with status ${response.status}`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) {
          errorDetail = typeof errorJson.detail === 'string' 
            ? errorJson.detail 
            : JSON.stringify(errorJson.detail);
        }
      } catch {
        // Fallback to text
        const text = await response.text();
        if (text) errorDetail = text;
      }
      throw new Error(errorDetail);
    }

    return await response.json();
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error('Unable to connect to the DermaSense server. Please ensure the backend is running.');
    }
    throw err;
  }
}

/**
 * Fetches condition catalog from /api/conditions.
 */
export async function fetchConditions() {
  try {
    const response = await fetch(`${API_BASE}/api/conditions`);
    if (!response.ok) {
      throw new Error(`Failed to load condition guides (${response.status})`);
    }
    return await response.json();
  } catch (err) {
    console.warn('Could not fetch conditions catalog:', err);
    return { conditions: [], total: 0, disclaimer: '' };
  }
}

/**
 * Fetches health status from /api/health.
 */
export async function fetchHealth() {
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    if (!response.ok) {
      throw new Error(`Health check returned status ${response.status}`);
    }
    return await response.json();
  } catch (err) {
    console.warn('Backend health check error:', err);
    return { status: 'offline', model_loaded: false };
  }
}

/**
 * Submits user or clinician feedback to /api/feedback.
 */
export async function submitFeedback(payload) {
  const response = await fetch(`${API_BASE}/api/feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Failed to submit feedback (${response.status})`);
  }

  return await response.json();
}

/**
 * Sends a query to the RAG knowledge base chatbot.
 */
export async function sendChatMessage(message, detectedCondition = null, language = 'en') {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      detected_condition: detectedCondition,
      language,
    }),
  });

  if (!response.ok) {
    let errorMsg = `Chat request failed (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) errorMsg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Loads UI translation strings.
 */
export async function fetchTranslations() {
  try {
    const response = await fetch(`${API_BASE}/api/translations`);
    if (response.ok) {
      return await response.json();
    }
  } catch (err) {
    console.warn('Could not fetch remote translations:', err);
  }
  return null;
}

/**
 * Submits an anonymized telemetry record strictly upon explicit citizen opt-in.
 */
export async function submitTelemetryOptIn(consent, conditionId, conditionName, region) {
  const response = await fetch(`${API_BASE}/api/telemetry/opt-in`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      consent,
      condition_id: conditionId,
      condition_name: conditionName,
      region,
    }),
  });

  if (!response.ok) {
    let errorMsg = `Telemetry submission failed (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) errorMsg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Verifies admin password.
 */
export async function verifyAdminPassword(password) {
  const response = await fetch(`${API_BASE}/api/admin/verify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ password }),
  });

  if (!response.ok) {
    throw new Error(`Verification failed (${response.status})`);
  }

  return await response.json();
}

/**
 * Fetches admin epidemiological metrics and spike alerts.
 */
export async function fetchAdminMetrics(password) {
  const response = await fetch(`${API_BASE}/api/admin/metrics`, {
    headers: {
      'X-Admin-Password': password,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Invalid administrator password.');
    }
    throw new Error(`Failed to load admin metrics (${response.status})`);
  }

  return await response.json();
}


