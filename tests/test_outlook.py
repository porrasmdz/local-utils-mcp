import unittest
from unittest.mock import patch

from services import outlook


def _message(index: int):
    return {
        "id": f"message-{index}",
        "subject": f"Subject {index}",
        "sender": {
            "emailAddress": {
                "name": f"Sender {index}",
                "address": f"sender{index}@example.com",
            }
        },
        "receivedDateTime": f"2026-09-{index:02d}T12:00:00Z",
        "isRead": index % 2 == 0,
    }


class OutlookMailPaginationTest(unittest.TestCase):
    def test_list_mails_defaults_to_first_page_of_ten(self):
        messages = [_message(index) for index in range(1, 12)]

        with patch.object(outlook, "graph_get", return_value={"value": messages}) as graph_get:
            result = outlook.list_mails_in_folder("user@example.com")

        graph_get.assert_called_once()
        endpoint, = graph_get.call_args.args
        params = graph_get.call_args.kwargs["params"]

        self.assertEqual(endpoint, "/users/user@example.com/mailFolders/inbox/messages")
        self.assertEqual(params["$top"], 11)
        self.assertEqual(params["$skip"], 0)
        self.assertEqual(params["$orderby"], "receivedDateTime desc")
        self.assertIsInstance(result, outlook.OutlookMailsPage)
        self.assertEqual(len(result.mails), 10)
        self.assertEqual(result.page, 1)
        self.assertEqual(result.page_size, 10)
        self.assertTrue(result.has_next_page)
        self.assertEqual(result.mails[0]["entry_id"], "message-1")

    def test_list_mails_uses_page_skip_and_page_size(self):
        messages = [_message(index) for index in range(1, 6)]

        with patch.object(outlook, "graph_get", return_value={"value": messages}) as graph_get:
            result = outlook.list_mails_in_folder(
                "user@example.com",
                page=3,
                page_size=5,
            )

        params = graph_get.call_args.kwargs["params"]
        self.assertEqual(params["$top"], 6)
        self.assertEqual(params["$skip"], 10)
        self.assertEqual(len(result.mails), 5)
        self.assertFalse(result.has_next_page)

    def test_list_mails_keeps_filters_with_pagination(self):
        with patch.object(outlook, "graph_get", return_value={"value": []}) as graph_get:
            outlook.list_mails_in_folder(
                "user@example.com",
                filters=[
                    outlook.OutlookFilter(
                        field="subject",
                        operator="LIKE",
                        value="invoice",
                    )
                ],
                page_size=20,
            )

        params = graph_get.call_args.kwargs["params"]
        self.assertEqual(params["$top"], 21)
        self.assertEqual(params["$filter"], "contains(subject, 'invoice')")

    def test_list_mails_resolves_named_folder_before_listing(self):
        folders_response = {
            "value": [{
                "id": "folder-1",
                "displayName": "Archive",
            }]
        }
        messages_response = {"value": [_message(1)]}

        with patch.object(outlook, "graph_get", side_effect=[folders_response, messages_response]) as graph_get:
            result = outlook.list_mails_in_folder(
                "user@example.com",
                folder_name="Archive",
            )

        self.assertEqual(graph_get.call_args_list[0].args[0], "/users/user@example.com/mailFolders?$top=100")
        self.assertEqual(graph_get.call_args_list[1].args[0], "/users/user@example.com/mailFolders/folder-1/messages")
        self.assertEqual(len(result.mails), 1)

    def test_list_mails_rejects_page_size_above_default_max(self):
        with patch.dict(outlook.os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "no puede exceder 100"):
                outlook.list_mails_in_folder("user@example.com", page_size=101)

    def test_list_mails_allows_configurable_max_page_size(self):
        messages = [_message(index) for index in range(1, 151)]

        with patch.dict(outlook.os.environ, {"OUTLOOK_MAILS_MAX_PAGE_SIZE": "150"}):
            with patch.object(outlook, "graph_get", return_value={"value": messages}) as graph_get:
                result = outlook.list_mails_in_folder("user@example.com", page_size=150)

        params = graph_get.call_args.kwargs["params"]
        self.assertEqual(params["$top"], 151)
        self.assertEqual(len(result.mails), 150)
        self.assertEqual(result.page_size, 150)
        self.assertFalse(result.has_next_page)

    def test_list_mails_rejects_invalid_page(self):
        with self.assertRaisesRegex(ValueError, "pagina"):
            outlook.list_mails_in_folder("user@example.com", page=0)


if __name__ == "__main__":
    unittest.main()
