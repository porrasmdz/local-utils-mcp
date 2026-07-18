import asyncio
from fastmcp import Client

# Inicializa el cliente que se conecta al servidor local en ejecución
client = Client("http://localhost:8000/sse")

async def test_mcp_tools():
    async with client:
        print("--- 1. Listando todas las cuentas registradas en el cliente Outlook ---")
        try:
            accounts_result = await client.call_tool("list_accounts_in_client")
            print("Resultado:", accounts_result)
        except Exception as e:
            print("Error al listar cuentas:", e)

        print("\n--- 2. Listando los correos más recientes en la Bandeja de entrada de una cuenta ---")
        try:
            # Reemplaza 'tu_correo@ejemplo.com' con tu dirección configurada en Outlook
            mails_result = await client.call_tool("list_mails_in_folder", {
                "account": "tu_correo@ejemplo.com",
                "folder_name": "Bandeja de entrada",
                "limit": 5
            })
            print("Resultado:", mails_result)
        except Exception as e:
            print("Error al listar correos:", e)

        print("\n--- 3. Listando todas las columnas (listas) de un tablero de Trello ---")
        try:
            # Si se pasa None, usará el tablero por defecto configurado
            board_lists_result = await client.call_tool("get_trello_board_lists", {
                "board_id": None
            })
            print("Resultado:", board_lists_result)
        except Exception as e:
            print("Error al listar columnas del tablero:", e)

if __name__ == "__main__":
    asyncio.run(test_mcp_tools())