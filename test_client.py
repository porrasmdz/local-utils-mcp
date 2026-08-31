import asyncio
from fastmcp import Client

# Inicializa el cliente que se conecta al servidor local en ejecución
client = Client("http://localhost:8000/sse")

async def test_mcp_tools():
    async with client:
        print("--- Listando correos de anpomen@hotmail.com en la carpeta CorreosEspol ---")
        try:
            result = await client.call_tool("list_mails_in_folder", {
                "account": "anpomen@hotmail.com",
                "folder_name": "CorreosEspol"
            })
            print(result)
        except Exception as e:
            print("Error al listar correos de la carpeta:", e)

if __name__ == "__main__":
    asyncio.run(test_mcp_tools())