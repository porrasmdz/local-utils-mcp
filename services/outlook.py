import os
import base64
import datetime
from typing import Any, List, Literal, Dict, Annotated, Optional
from pydantic import BaseModel, EmailStr, Field
from bs4 import BeautifulSoup

from services.graph_client import graph_get, graph_post, graph_patch, graph_delete

DEFAULT_EVENTS_LIMIT = 15
DEFAULT_OUTLOOK_MAILS_PAGE_SIZE = 10
DEFAULT_OUTLOOK_MAILS_MAX_PAGE_SIZE = 100
OUTLOOK_MAILS_MAX_PAGE_SIZE_ENV = "OUTLOOK_MAILS_MAX_PAGE_SIZE"

def _user_path(account: Optional[str] = None) -> str:
    if account:
        return f"/users/{account}"
    tenant_id = os.getenv("MS_GRAPH_TENANT_ID", "").lower()
    if tenant_id == "consumers":
        return "/me"
    target = os.getenv("MS_GRAPH_USER_EMAIL")
    if target:
        return f"/users/{target}"
    return "/me"


def _get_outlook_mails_max_page_size() -> int:
    raw_max = os.getenv(OUTLOOK_MAILS_MAX_PAGE_SIZE_ENV)
    if raw_max is None:
        return DEFAULT_OUTLOOK_MAILS_MAX_PAGE_SIZE

    try:
        configured_max = int(raw_max)
    except ValueError:
        return DEFAULT_OUTLOOK_MAILS_MAX_PAGE_SIZE

    if configured_max < 1:
        return DEFAULT_OUTLOOK_MAILS_MAX_PAGE_SIZE

    return configured_max


def _validate_outlook_mails_pagination(page: int, page_size: int) -> tuple[int, int, int]:
    max_page_size = _get_outlook_mails_max_page_size()
    if page < 1:
        raise ValueError("La pagina debe ser mayor o igual a 1.")
    if page_size < 1:
        raise ValueError("La cantidad de correos por pagina debe ser mayor o igual a 1.")
    if page_size > max_page_size:
        raise ValueError(
            f"La cantidad de correos por pagina no puede exceder {max_page_size}. "
            f"Configure {OUTLOOK_MAILS_MAX_PAGE_SIZE_ENV} para cambiar este limite."
        )

    return page, page_size, max_page_size


class OutlookFilter(BaseModel):
    field: Literal["subject", "body", "sender_email", "sender_name", 
        "unread", "received_time", "has_attachment", "entry_id" 
    ] = Field(..., description="El campo por el cual filtrar los correos.")
    operator: Literal["=", "!=", "LIKE", ">=", "<=", ">", "<"
                      ] = Field(..., description="Operador lógico para la comparación.")
    value: str = Field(..., description="El valor contra el cual comparar (ej. 'sostenibilidad', 'true', '00000000D9...').")


class OutlookMailsPage(BaseModel):
    mails: List[Dict[str, Any]] = Field(default_factory=list, description="Correos de la pagina solicitada.")
    page: int = Field(..., description="Numero de pagina retornado, basado en 1.")
    page_size: int = Field(..., description="Cantidad de correos por pagina aplicada.")
    has_next_page: bool = Field(..., description="Indica si existe una pagina siguiente.")


class CreateEmailDto(BaseModel):
    to: str = Field(..., description="Dirección(es) de correo del destinatario (separadas por punto y coma si son varias).")
    subject: str = Field(..., description="Asunto del correo electrónico.")
    body: str = Field(..., description="Cuerpo en texto plano del correo electrónico.")
    html_body: Optional[str] = Field(None, description="Cuerpo en formato HTML opcional (si se proporciona, complementará o reemplazará al cuerpo en texto plano).")
    cc: Optional[str] = Field(None, description="Dirección(es) de correo para copia (CC), separadas por punto y coma.")
    bcc: Optional[str] = Field(None, description="Dirección(es) de correo para copia oculta (BCC), separadas por punto y coma.")
    importance: Optional[Literal["low", "normal", "high"]] = Field(None, description="Nivel de importancia del correo.")
    sensitivity: Optional[Literal["normal", "personal", "private", "confidential"]] = Field(None, description="Nivel de confidencialidad/sensibilidad del correo.")
    account: Optional[str] = Field(None, description="Dirección de correo o nombre de la cuenta configurada en Outlook desde la cual enviar el correo.")
    attachments: Optional[List[str]] = Field(None, description="Lista de rutas absolutas de archivos locales para adjuntar.")
    categories: Optional[str] = Field(None, description="Categorías asociadas al correo (separadas por comas).")
    read_receipt_requested: Optional[bool] = Field(None, description="Si es True, solicita confirmación de lectura.")
    delivery_report_requested: Optional[bool] = Field(None, description="Si es True, solicita informe de entrega.")
    save_as_draft: Optional[bool] = Field(False, description="Si es True, el correo se guardará en borradores (Drafts) en lugar de enviarse inmediatamente.")

def list_accounts_in_client() -> List[str]:
    """
    Lista las cuentas registradas en el tenant de Microsoft Graph API o la cuenta configurada por defecto.
    """
    default_email = os.getenv("MS_GRAPH_USER_EMAIL")
    try:
        data = graph_get("/users?$select=userPrincipalName,mail")
        users = data.get("value", [])
        accounts = []
        for u in users:
            email = u.get("mail") or u.get("userPrincipalName")
            if email:
                accounts.append(email)
        if accounts:
            return accounts
    except Exception:
        pass
    if default_email:
        return [default_email]
    return ["me"]

def list_folders_from_account(
    account: Annotated[EmailStr, Field(description="Dirección de correo electrónico de la cuenta a consultar.")]
) -> List[Dict[str, Any]]:
    """
    Lista las carpetas de correo disponibles en la cuenta de Microsoft Graph API especificada.
    """
    base_path = _user_path(account)
    res = graph_get(f"{base_path}/mailFolders?$top=100")
    folders = res.get("value", [])
    
    result = []
    for f in folders:
        result.append({
            "folder_name": f.get("displayName"),
            "mail_count": f.get("totalItemCount", 0),
            "folder_id": f.get("id")
        })
    return result

def list_mails_in_folder(
    account: Annotated[str, Field(description="Direccion de correo electronico o nombre de la cuenta a consultar.")],
    filters: Annotated[Optional[List[OutlookFilter]], Field(description="Lista opcional de filtros estructurados para buscar correos especificos.")] = None,
    folder_name: Annotated[Optional[str], Field(description="Nombre de la carpeta a consultar. Si es None, consulta inbox.")] = None,
    page: Annotated[int, Field(description="Pagina a retornar, basada en 1.")] = 1,
    page_size: Annotated[int, Field(description="Correos por pagina. Default 10. No puede exceder OUTLOOK_MAILS_MAX_PAGE_SIZE, o 100 si la variable no existe.")] = DEFAULT_OUTLOOK_MAILS_PAGE_SIZE
) -> OutlookMailsPage:
    """
    Lista correos de una carpeta de una cuenta usando Microsoft Graph API con paginacion.
    """
    base_path = _user_path(account)
    page, page_size, max_page_size = _validate_outlook_mails_pagination(page, page_size)

    if not folder_name or folder_name.lower() in ["bandeja de entrada", "inbox"]:
        folder_endpoint = f"{base_path}/mailFolders/inbox/messages"
    else:
        folders_res = graph_get(f"{base_path}/mailFolders?$top=100")
        target_id = None
        for f in folders_res.get("value", []):
            if f.get("displayName", "").lower() == folder_name.lower():
                target_id = f.get("id")
                break
        if target_id:
            folder_endpoint = f"{base_path}/mailFolders/{target_id}/messages"
        else:
            folder_endpoint = f"{base_path}/messages"

    page_start = (page - 1) * page_size
    params = {
        "$top": page_size + 1,
        "$skip": page_start,
        "$orderby": "receivedDateTime desc",
        "$select": "id,subject,sender,receivedDateTime,isRead"
    }

    filter_parts = []
    if filters:
        for f in filters:
            val_clean = f.value.replace("'", "''")
            if f.field == "subject":
                filter_parts.append(f"contains(subject, '{val_clean}')")
            elif f.field == "body":
                filter_parts.append(f"contains(body/content, '{val_clean}')")
            elif f.field == "sender_email":
                filter_parts.append(f"sender/emailAddress/address eq '{val_clean}'")
            elif f.field == "sender_name":
                filter_parts.append(f"contains(sender/emailAddress/name, '{val_clean}')")
            elif f.field == "unread":
                is_unread = val_clean.lower() in ["true", "1"]
                filter_parts.append(f"isRead eq {'false' if is_unread else 'true'}")
            elif f.field == "entry_id":
                filter_parts.append(f"id eq '{val_clean}'")

    if filter_parts:
        params["$filter"] = " and ".join(filter_parts)

    res = graph_get(folder_endpoint, params=params)
    messages = res.get("value", [])
    has_next_page = len(messages) > page_size
    page_messages = messages[:page_size]

    emails_list = []
    for msg in page_messages:
        sender_info = msg.get("sender", {}).get("emailAddress", {})
        emails_list.append({
            "subject": msg.get("subject", ""),
            "sender_name": sender_info.get("name", ""),
            "sender_email": sender_info.get("address", ""),
            "received_time": msg.get("receivedDateTime", ""),
            "unread": not msg.get("isRead", True),
            "entry_id": msg.get("id")
        })

    print(f"\n================ [MCP OUTLOOK MAILS] ================")
    print(f"Cuenta: {account}")
    print(f"Carpeta: {folder_name or 'inbox'}")
    print(f"Correos devueltos: {len(emails_list)}")
    print(f"Pagina: {page} - Page size: {page_size} - Max page size: {max_page_size}")
    print(f"Has next page: {has_next_page}")
    print(f"=====================================================\n")

    return OutlookMailsPage(
        mails=emails_list,
        page=page,
        page_size=page_size,
        has_next_page=has_next_page,
    )

def get_email_body_by_id(
    account: Annotated[str, Field(description="Nombre o dirección de correo de la cuenta a la que pertenece el correo.")],
    entry_id: Annotated[str, Field(description="El identificador único del correo (Graph Message ID).")]
) -> Dict[str, Any]:
    """
    Recupera y analiza el contenido y los metadatos de un correo específico usando Microsoft Graph API.
    """
    base_path = _user_path(account)
    msg = graph_get(f"{base_path}/messages/{entry_id}?$expand=attachments")

    body_obj = msg.get("body", {})
    raw_body = body_obj.get("content", "")
    content_type = body_obj.get("contentType", "text").lower()

    if content_type == "html":
        soup = BeautifulSoup(raw_body, 'html.parser')
        plain_text = soup.get_text()
        html_content = raw_body
    else:
        plain_text = raw_body
        html_content = ""

    body_preview = plain_text[:200].strip()

    extracted_links = []
    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if href.lower().startswith(('http://', 'https://', 'mailto:')):
                text = a_tag.get_text().strip()
                extracted_links.append({
                    "url": href,
                    "text": f"<anchor_text>{text or '[Sin texto]'}</anchor_text>"
                })

    attachments_list = []
    raw_attachments = msg.get("attachments", [])
    for att in raw_attachments:
        attachments_list.append({
            "filename": att.get("name", ""),
            "type": att.get("contentType", ""),
            "size_bytes": att.get("size", 0)
        })

    return {
        "subject": msg.get("subject", ""),
        "body_preview": f"<untrusted_body>{body_preview}</untrusted_body>",
        "total_links": len(extracted_links),
        "links": extracted_links,
        "attachments_count": len(attachments_list),
        "attachments": attachments_list
    }

def write_email_to(email_data: CreateEmailDto) -> Dict[str, Any]:
    """
    Crea y envía (o guarda en borradores) un correo electrónico usando Microsoft Graph API.
    """
    base_path = _user_path(email_data.account)

    to_list = [{"emailAddress": {"address": addr.strip()}} for addr in email_data.to.split(";") if addr.strip()]
    cc_list = [{"emailAddress": {"address": addr.strip()}} for addr in email_data.cc.split(";")] if email_data.cc else []
    bcc_list = [{"emailAddress": {"address": addr.strip()}} for addr in email_data.bcc.split(";")] if email_data.bcc else []

    message_payload: Dict[str, Any] = {
        "subject": email_data.subject,
        "body": {
            "contentType": "HTML" if email_data.html_body else "Text",
            "content": email_data.html_body if email_data.html_body else email_data.body
        },
        "toRecipients": to_list,
        "ccRecipients": cc_list,
        "bccRecipients": bcc_list
    }

    if email_data.importance:
        message_payload["importance"] = email_data.importance.lower()

    if email_data.attachments:
        att_payloads = []
        for file_path in email_data.attachments:
            if not os.path.isabs(file_path):
                raise ValueError(f"La ruta del archivo adjunto debe ser absoluta: '{file_path}'")
            if not os.path.exists(file_path):
                raise ValueError(f"El archivo adjunto no existe: '{file_path}'")
            with open(file_path, "rb") as f:
                encoded_content = base64.b64encode(f.read()).decode("utf-8")
            att_payloads.append({
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": os.path.basename(file_path),
                "contentBytes": encoded_content
            })
        message_payload["attachments"] = att_payloads

    if email_data.save_as_draft:
        graph_post(f"{base_path}/messages", message_payload)
        action_done = "guardado en borradores"
    else:
        send_payload = {
            "message": message_payload,
            "saveToSentItems": "true"
        }
        graph_post(f"{base_path}/sendMail", send_payload)
        action_done = "enviado"

    return {
        "status": "success",
        "message": f"Correo {action_done} exitosamente vía Graph API.",
        "details": {
            "to": email_data.to,
            "subject": email_data.subject,
            "account": email_data.account or "Cuenta predeterminada",
            "action": action_done
        }
    }

class CalendarFilterDto(BaseModel):
    field: Literal["subject", "location", "body", "categories", "busy_status", "sensitivity"] = Field(..., description="El campo por el cual filtrar.")
    operator: Literal["=", "!=", "LIKE", ">=", "<=", ">", "<"] = Field(..., description="Operador lógico.")
    value: str = Field(..., description="El valor contra el cual comparar.")

class CalendarQueryDto(BaseModel):
    account: str = Field(..., description="Dirección de correo de la cuenta a consultar.")
    start_date: Optional[str] = Field(None, description="Fecha/hora de inicio 'YYYY-MM-DD HH:MM' o 'YYYY-MM-DD'. Por defecto es el día actual.")
    end_date: Optional[str] = Field(None, description="Fecha/hora de fin 'YYYY-MM-DD HH:MM' o 'YYYY-MM-DD'. Por defecto es 7 días después de start_date.")
    filters: Optional[List[CalendarFilterDto]] = Field(None, description="Filtros adicionales.")
    limit: Optional[int] = Field(DEFAULT_EVENTS_LIMIT, description="Número máximo de eventos.")

class CreateAppointmentDto(BaseModel):
    subject: str = Field(..., description="Asunto del evento de calendario.")
    start: str = Field(..., description="Fecha y hora de inicio en formato 'YYYY-MM-DD HH:MM' o 'YYYY-MM-DD'.")
    duration: int = Field(..., description="Duración del evento en minutos.")
    body: Optional[str] = Field(None, description="Descripción del evento.")
    location: Optional[str] = Field(None, description="Ubicación o enlace de reunión.")
    all_day_event: Optional[bool] = Field(False, description="Si es True, el evento ocupará todo el día.")
    reminder_set: Optional[bool] = Field(True, description="Si es True, activa un recordatorio para el evento.")
    reminder_minutes_before_start: Optional[int] = Field(15, description="Minutos antes del evento para activar el recordatorio.")
    busy_status: Optional[Literal["free", "tentative", "busy", "out_of_office", "working_elsewhere"]] = Field("busy", description="Estado de disponibilidad.")
    sensitivity: Optional[Literal["normal", "personal", "private", "confidential"]] = Field("normal", description="Nivel de privacidad/sensibilidad.")
    categories: Optional[str] = Field(None, description="Categorías del evento separadas por comas.")
    attendees: Optional[List[str]] = Field(None, description="Lista de correos electrónicos de los invitados.")
    is_meeting: Optional[bool] = Field(False, description="Si es True, convierte el evento en reunión.")
    account: Optional[str] = Field(None, description="Cuenta específica desde la cual crear el evento.")

class UpdateAppointmentDto(BaseModel):
    subject: Optional[str] = Field(None, description="Nuevo asunto del evento.")
    start: Optional[str] = Field(None, description="Nueva fecha/hora de inicio 'YYYY-MM-DD HH:MM' o 'YYYY-MM-DD'.")
    duration: Optional[int] = Field(None, description="Nueva duración en minutos.")
    body: Optional[str] = Field(None, description="Nueva descripción del evento.")
    location: Optional[str] = Field(None, description="Nueva ubicación.")
    all_day_event: Optional[bool] = Field(None, description="Si es True, convierte a evento de todo el día.")
    reminder_set: Optional[bool] = Field(None, description="Activa o desactiva el recordatorio.")
    reminder_minutes_before_start: Optional[int] = Field(None, description="Nuevos minutos antes para el recordatorio.")
    busy_status: Optional[Literal["free", "tentative", "busy", "out_of_office", "working_elsewhere"]] = Field(None, description="Nuevo estado de disponibilidad.")
    sensitivity: Optional[Literal["normal", "personal", "private", "confidential"]] = Field(None, description="Nuevo nivel de privacidad.")
    categories: Optional[str] = Field(None, description="Nuevas categorías.")
    attendees: Optional[List[str]] = Field(None, description="Nueva lista de correos de invitados.")
    send_updates: Optional[bool] = Field(True, description="Si es True, envía actualizaciones a los invitados.")

def list_calendar_events(query_data: CalendarQueryDto) -> List[Dict[str, Any]]:
    """
    Lista eventos del calendario en un rango de fechas usando Microsoft Graph API.
    """
    base_path = _user_path(query_data.account)

    now = datetime.datetime.now()
    default_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    def parse_dt(date_str: Optional[str], default_val: datetime.datetime) -> datetime.datetime:
        if not date_str:
            return default_val
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return default_val

    start_dt = parse_dt(query_data.start_date, default_start)
    end_dt = parse_dt(query_data.end_date, start_dt + datetime.timedelta(days=7))

    start_iso = start_dt.isoformat() + "Z"
    end_iso = end_dt.isoformat() + "Z"

    params = {
        "startDateTime": start_iso,
        "endDateTime": end_iso,
        "$top": query_data.limit or 50,
        "$orderby": "start/dateTime asc"
    }

    res = graph_get(f"{base_path}/calendarView", params=params)
    events = res.get("value", [])

    events_list = []
    busy_map_graph = {"free": "free", "tentative": "tentative", "busy": "busy", "oof": "out_of_office", "workingElsewhere": "working_elsewhere"}

    for ev in events:
        attendees_list = [att.get("emailAddress", {}).get("address", "") for att in ev.get("attendees", [])]
        events_list.append({
            "entry_id": ev.get("id"),
            "subject": ev.get("subject", ""),
            "start": ev.get("start", {}).get("dateTime", ""),
            "end": ev.get("end", {}).get("dateTime", ""),
            "duration": 0,
            "location": ev.get("location", {}).get("displayName", ""),
            "all_day_event": ev.get("isAllDay", False),
            "body": ev.get("body", {}).get("content", ""),
            "busy_status": busy_map_graph.get(ev.get("showAs", "busy"), "busy"),
            "sensitivity": ev.get("sensitivity", "normal"),
            "categories": ",".join(ev.get("categories", [])),
            "reminder_set": ev.get("isReminderOn", True),
            "reminder_minutes_before_start": ev.get("reminderMinutesBeforeStart", 15),
            "attendees": attendees_list,
            "is_meeting": len(attendees_list) > 0
        })

    return events_list

def create_calendar_event(event_data: CreateAppointmentDto) -> Dict[str, Any]:
    """
    Crea un nuevo evento o reunión en el calendario usando Microsoft Graph API.
    """
    base_path = _user_path(event_data.account)

    start_dt = None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            start_dt = datetime.datetime.strptime(event_data.start, fmt)
            break
        except ValueError:
            continue
    if not start_dt:
        raise ValueError(f"Formato de fecha de inicio inválido: '{event_data.start}'")

    end_dt = start_dt + datetime.timedelta(minutes=event_data.duration)

    busy_graph = {
        "free": "free",
        "tentative": "tentative",
        "busy": "busy",
        "out_of_office": "oof",
        "working_elsewhere": "workingElsewhere"
    }

    event_payload: Dict[str, Any] = {
        "subject": event_data.subject,
        "body": {
            "contentType": "HTML",
            "content": event_data.body or ""
        },
        "start": {
            "dateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "UTC"
        },
        "isAllDay": event_data.all_day_event,
        "isReminderOn": event_data.reminder_set if event_data.reminder_set is not None else True,
        "reminderMinutesBeforeStart": event_data.reminder_minutes_before_start or 15,
        "showAs": busy_graph.get(event_data.busy_status or "busy", "busy")
    }

    if event_data.location:
        event_payload["location"] = {"displayName": event_data.location}

    if event_data.attendees:
        event_payload["attendees"] = [
            {"emailAddress": {"address": att}, "type": "required"}
            for att in event_data.attendees
        ]

    created = graph_post(f"{base_path}/events", event_payload)

    return {
        "status": "success",
        "message": "Cita/reunión creada exitosamente vía Graph API.",
        "details": {
            "entry_id": created.get("id"),
            "subject": created.get("subject"),
            "start": created.get("start", {}).get("dateTime"),
            "duration": event_data.duration,
            "location": event_data.location
        }
    }

def edit_calendar_event(
    account: str,
    entry_id: str,
    updates: UpdateAppointmentDto
) -> Dict[str, Any]:
    """
    Edita un evento existente en el calendario usando Microsoft Graph API.
    """
    base_path = _user_path(account)

    patch_payload: Dict[str, Any] = {}

    if updates.subject is not None:
        patch_payload["subject"] = updates.subject

    if updates.body is not None:
        patch_payload["body"] = {"contentType": "HTML", "content": updates.body}

    if updates.location is not None:
        patch_payload["location"] = {"displayName": updates.location}

    if updates.all_day_event is not None:
        patch_payload["isAllDay"] = updates.all_day_event

    if updates.reminder_set is not None:
        patch_payload["isReminderOn"] = updates.reminder_set

    if updates.reminder_minutes_before_start is not None:
        patch_payload["reminderMinutesBeforeStart"] = updates.reminder_minutes_before_start

    if updates.start is not None and updates.duration is not None:
        start_dt = None
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                start_dt = datetime.datetime.strptime(updates.start, fmt)
                break
            except ValueError:
                continue
        if start_dt:
            end_dt = start_dt + datetime.timedelta(minutes=updates.duration)
            patch_payload["start"] = {"dateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "UTC"}
            patch_payload["end"] = {"dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "UTC"}

    if updates.attendees is not None:
        patch_payload["attendees"] = [
            {"emailAddress": {"address": att}, "type": "required"}
            for att in updates.attendees
        ]

    updated = graph_patch(f"{base_path}/events/{entry_id}", patch_payload)

    return {
        "status": "success",
        "message": "Cita/reunión actualizada exitosamente vía Graph API.",
        "details": {
            "entry_id": updated.get("id"),
            "subject": updated.get("subject")
        }
    }
