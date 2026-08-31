import os
import atexit
from typing import Dict, Any, Optional
import msal

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".msal_cache.bin")
APPLICATION_SCOPES = ["https://graph.microsoft.com/.default"]
DELEGATED_SCOPES = [
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/Mail.Send",
    "https://graph.microsoft.com/Calendars.ReadWrite",
    "https://graph.microsoft.com/User.Read"
]

def get_graph_credentials() -> Dict[str, str]:
    """Obtiene las credenciales de Microsoft Graph API desde las variables de entorno."""
    tenant_id = os.getenv("MS_GRAPH_TENANT_ID", "consumers")
    client_id = os.getenv("MS_GRAPH_CLIENT_ID")
    client_secret = os.getenv("MS_GRAPH_CLIENT_SECRET")

    missing = []
    if not client_id:
        missing.append("MS_GRAPH_CLIENT_ID")

    if missing:
        raise ValueError(
            f"Faltan las siguientes variables de entorno para Microsoft Graph API: {', '.join(missing)}. "
            f"Por favor configurarlas en tu archivo .env"
        )

    return {
        "tenant_id": tenant_id,
        "client_id": client_id,
        "client_secret": client_secret or "",
    }

def _get_token_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache.deserialize(f.read())
        except Exception:
            pass
    return cache

def _save_token_cache(cache: msal.SerializableTokenCache) -> None:
    if cache.has_state_changed:
        try:
            with open(CACHE_FILE, "w") as f:
                f.write(cache.serialize())
        except Exception:
            pass

def get_access_token() -> str:
    """
    Obtiene un access token de Microsoft Graph API.
    Soporta:
    1. Delegated Flow (Device Code Flow con almacenamiento en caché) para cuentas personales (tenant_id='consumers').
    2. Client Credentials Flow para cuentas de trabajo/organización (Azure AD / Entra ID).
    """
    creds = get_graph_credentials()
    tenant_id = creds["tenant_id"].lower()

    # Si tenant_id es 'consumers', o la cuenta es personal (@hotmail, @outlook, @live),
    # se requiere el flujo delegado (Device Code Flow) porque Microsoft Graph API
    # no permite Client Credentials en cuentas personales.
    if tenant_id == "consumers":
        authority = "https://login.microsoftonline.com/consumers"
        cache = _get_token_cache()
        app = msal.PublicClientApplication(
            client_id=creds["client_id"],
            authority=authority,
            token_cache=cache
        )

        accounts = app.get_accounts()
        result = None
        if accounts:
            result = app.acquire_token_silent(DELEGATED_SCOPES, account=accounts[0])

        if not result or "access_token" not in result:
            flow = app.initiate_device_flow(scopes=DELEGATED_SCOPES)
            if "user_code" not in flow:
                raise RuntimeError(f"Error al iniciar el inicio de sesión por Device Code: {flow.get('error_description', flow)}")
            
            print("\n=======================================================")
            print("AUTENTICACION DE CUENTA PERSONAL REQUERIDA")
            print(flow["message"])
            print("=======================================================\n")
            
            result = app.acquire_token_by_device_flow(flow)

        _save_token_cache(cache)

        if result and "access_token" in result:
            return result["access_token"]
        else:
            error_desc = result.get("error_description", result.get("error", "Error desconocido")) if result else "No result"
            raise RuntimeError(f"Error al obtener token de Microsoft Graph API (Delegado): {error_desc}")

    # Flujo de Client Credentials para cuentas corporativas/organizacionales (Entra ID)
    authority = f"https://login.microsoftonline.com/{creds['tenant_id']}"
    app = msal.ConfidentialClientApplication(
        client_id=creds["client_id"],
        client_credential=creds["client_secret"],
        authority=authority
    )

    result = app.acquire_token_for_client(scopes=APPLICATION_SCOPES)

    if "access_token" in result:
        return result["access_token"]
    else:
        error_desc = result.get("error_description", result.get("error", "Error desconocido"))
        raise RuntimeError(f"Error al obtener token de Microsoft Graph API (Client Credentials): {error_desc}")

