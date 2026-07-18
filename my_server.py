from dotenv import load_dotenv
load_dotenv()
from fastmcp import FastMCP
from services.outlook import get_email_body_by_id, list_accounts_in_client, list_folders_from_account, list_mails_in_folder 
from services.trello import get_trello_board_lists, get_trello_cards_in_list, get_trello_card_by_id \
    , get_trello_boards, write_trello_card_in_list, update_trello_card, attach_file_to_trello_card

mcp = FastMCP( "Local Windows Utils",
               instructions="Provides tools for interacting with local applications and work apps.",
               tools=[
                   list_accounts_in_client, list_folders_from_account, 
                   list_mails_in_folder, get_email_body_by_id,
                   get_trello_card_by_id, get_trello_board_lists, get_trello_cards_in_list,
                   get_trello_boards, write_trello_card_in_list, update_trello_card,
                   attach_file_to_trello_card
                   ]
) 

if __name__ == "__main__":
    mcp.run(transport="sse", port=8000)