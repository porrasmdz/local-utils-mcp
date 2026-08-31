from typing import Any, Dict, Optional
import httpx
from services.graph_auth import get_access_token

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

def _get_headers() -> Dict[str, str]:
    token = get_access_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def _handle_response(response: httpx.Response) -> Any:
    if response.status_code == 204:
        return {}
        
    try:
        data = response.json()
    except Exception:
        data = {"raw_text": response.text}

    if not response.is_success:
        error_info = data.get("error", {})
        code = error_info.get("code", f"HTTP_{response.status_code}")
        message = error_info.get("message", response.text)
        raise RuntimeError(f"Error de Microsoft Graph API [{code}]: {message}")

    return data

def graph_get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Realiza una petición GET autenticada a Microsoft Graph API."""
    url = endpoint if endpoint.startswith("http") else f"{GRAPH_BASE_URL}{endpoint}"
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=_get_headers(), params=params)
        return _handle_response(response)

def graph_post(endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Any:
    """Realiza una petición POST autenticada a Microsoft Graph API."""
    url = endpoint if endpoint.startswith("http") else f"{GRAPH_BASE_URL}{endpoint}"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=_get_headers(), json=json_data)
        return _handle_response(response)

def graph_patch(endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Any:
    """Realiza una petición PATCH autenticada a Microsoft Graph API."""
    url = endpoint if endpoint.startswith("http") else f"{GRAPH_BASE_URL}{endpoint}"
    with httpx.Client(timeout=30.0) as client:
        response = client.patch(url, headers=_get_headers(), json=json_data)
        return _handle_response(response)

def graph_delete(endpoint: str) -> Any:
    """Realiza una petición DELETE autenticada a Microsoft Graph API."""
    url = endpoint if endpoint.startswith("http") else f"{GRAPH_BASE_URL}{endpoint}"
    with httpx.Client(timeout=30.0) as client:
        response = client.delete(url, headers=_get_headers())
        return _handle_response(response)
