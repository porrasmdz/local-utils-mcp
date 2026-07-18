import asyncio
from fastmcp import Client

# Inicializa el cliente que se conecta al servidor local en ejecución
client = Client("http://localhost:8000/sse")
TEST_CARD_ID = "6a5b077bb000f2e6f790cd53"
TEST_FILE_PATH = "media://inbound/image---15437760-929c-4f71-a5d4-607c41d55fc7.png"
TEST_FILENAME = "myeclipse_2026_evidence.png"
async def test_mcp_tools():
    async with client:
        print("--- 1. Listando todas las cuentas registradas en el cliente Outlook ---")
        try:
            board_lists_result = await client.call_tool("attach_file_to_trello_card", {
                "card_id":TEST_CARD_ID,
                "file_uri":TEST_FILE_PATH,
                "filename":TEST_FILENAME
            })
            print(board_lists_result)
        except Exception as e:
            print("Error al listar columnas del tablero:", e)

if __name__ == "__main__":
    asyncio.run(test_mcp_tools())