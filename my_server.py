from dotenv import load_dotenv
load_dotenv()
from fastmcp import FastMCP
from services.excel import read_excel_sheet_rows, summarize_excel_workbook, update_excel_sheet_cells
from services.outlook import get_email_body_by_id, list_accounts_in_client, list_folders_from_account, list_mails_in_folder, write_email_to, list_calendar_events, create_calendar_event, edit_calendar_event
from services.trello import get_trello_board_lists, get_trello_cards_in_list, get_trello_card_by_id, get_trello_board_members \
    , get_trello_boards, get_trello_users, count_trello_cards_in_lists, write_trello_card_in_list, update_trello_card, bulk_update_trello_cards, attach_file_to_trello_card

mcp = FastMCP( "Local Windows Utils",
               instructions="Provides tools for interacting with local applications and work apps.",
               tools=[
                   summarize_excel_workbook, read_excel_sheet_rows, update_excel_sheet_cells,
                   list_accounts_in_client, list_folders_from_account, 
                   list_mails_in_folder, get_email_body_by_id, write_email_to,
                   list_calendar_events, create_calendar_event, edit_calendar_event,
                   get_trello_card_by_id, get_trello_board_lists, get_trello_board_members, get_trello_cards_in_list,
                   get_trello_boards, get_trello_users, count_trello_cards_in_lists, write_trello_card_in_list, update_trello_card, bulk_update_trello_cards,
                   attach_file_to_trello_card
                   ]
) 

if __name__ == "__main__":
    mcp.run(transport="stdio")
