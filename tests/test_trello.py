import unittest
from unittest.mock import Mock, patch

from services import trello


class TrelloCardHelpersTest(unittest.TestCase):
    def test_parse_card_ids_strips_empty_values_and_deduplicates(self):
        self.assertEqual(
            trello._parse_card_ids(" card-1,card-2, card-1, ,card-3 "),
            ["card-1", "card-2", "card-3"],
        )

    def test_build_general_card_returns_model_with_compact_fields(self):
        result = trello._build_trello_general_card({
            "id": "card-1",
            "idList": "list-1",
            "name": "<card_name>Task</card_name>",
            "desc": "<card_desc>Description</card_desc>",
            "due": "2026-12-31T23:59:59.000Z",
            "dueComplete": False,
            "closed": False,
            "shortUrl": "https://trello.com/c/card-1",
            "members": [{
                "id": "member-1",
                "username": "apomen",
                "fullName": "Andres Pomen",
                "initials": "AP",
            }],
        })

        self.assertIsInstance(result, trello.TrelloGeneralCard)
        self.assertEqual(result.card_id, "card-1")
        self.assertEqual(result.list_id, "list-1")
        self.assertEqual(result.name, "<card_name>Task</card_name>")
        self.assertEqual(result.description_preview, "<card_desc>Description</card_desc>")
        self.assertEqual(result.due_date, "2026-12-31T23:59:59.000Z")
        self.assertEqual(result.url, "https://trello.com/c/card-1")
        self.assertEqual(result.assigned_user[0].user_id, "member-1")
        self.assertEqual(result.assigned_user[0].full_name, "Andres Pomen")
        self.assertFalse(hasattr(result, "description"))

    def test_build_detailed_card_returns_model_with_full_fields(self):
        result = trello._build_trello_detailed_card({
            "id": "card-1",
            "idList": "list-1",
            "name": "Task",
            "desc": "Full description",
            "due": None,
            "dueComplete": False,
            "closed": False,
            "members": [{"id": "member-1", "username": "apomen", "fullName": "Andres Pomen", "initials": "AP"}],
            "checklists": [{
                "id": "checklist-1",
                "name": "Checklist",
                "checkItems": [{"id": "item-1", "name": "Item", "state": "incomplete"}],
            }],
            "actions": [{
                "id": "comment-1",
                "type": "commentCard",
                "date": "2026-01-01T00:00:00.000Z",
                "memberCreator": {"fullName": "Author"},
                "data": {"text": "Comment"},
            }],
        })

        self.assertIsInstance(result, trello.TrelloDetailedCard)
        self.assertEqual(result.description, "<card_desc>Full description</card_desc>")
        self.assertEqual(result.assigned_user[0].username, "apomen")
        self.assertEqual(result.checklists[0].items[0].name, "<check_item>Item</check_item>")
        self.assertEqual(result.comments[0].text, "<comment_text>Comment</comment_text>")

    def test_assigned_user_filters_match_names_and_ids(self):
        card = trello.TrelloGeneralCard(
            card_id="card-1",
            name="<card_name>Task</card_name>",
            description_preview="<card_desc>Description</card_desc>",
            assigned_user=[trello.TrelloAssignedUser(
                user_id="member-1",
                username="apomen",
                full_name="Andres Pomen",
                initials="AP",
            )],
        )

        self.assertTrue(trello._matches_card_filter(card, trello.TrelloCardFilter(
            field="assigned_user",
            operator="LIKE",
            value="andres",
        )))
        self.assertTrue(trello._matches_card_filter(card, trello.TrelloCardFilter(
            field="assigned_user_id",
            operator="=",
            value="member-1",
        )))
        self.assertFalse(trello._matches_card_filter(card, trello.TrelloCardFilter(
            field="assigned_user_id",
            operator="=",
            value="member-2",
        )))


class TrelloCardBatchTest(unittest.TestCase):
    def test_single_card_keeps_model_response(self):
        card = trello.TrelloDetailedCard(
            card_id="card-1",
            name="<card_name>Task</card_name>",
            description_preview="<card_desc></card_desc>",
            description="<card_desc></card_desc>",
        )

        with patch.object(trello, "_get_single_trello_card_by_id", return_value=card) as get_single:
            result = trello.get_trello_card_by_id("card-1")

        self.assertIs(result, card)
        get_single.assert_called_once_with("card-1")

    def test_multiple_cards_are_read_with_five_workers(self):
        captured_workers = []

        class FakeExecutor:
            def __init__(self, max_workers):
                captured_workers.append(max_workers)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def map(self, fn, card_ids):
                return [fn(card_id) for card_id in card_ids]

        with patch.object(trello, "ThreadPoolExecutor", FakeExecutor):
            with patch.object(
                trello,
                "_get_single_trello_card_by_id",
                side_effect=lambda card_id: trello.TrelloDetailedCard(
                    card_id=card_id,
                    name=f"<card_name>{card_id}</card_name>",
                    description_preview="<card_desc></card_desc>",
                    description="<card_desc></card_desc>",
                ),
            ):
                result = trello.get_trello_card_by_id("card-1, card-2, card-3")

        self.assertEqual(captured_workers, [5])
        self.assertTrue(all(isinstance(card, trello.TrelloDetailedCard) for card in result))
        self.assertEqual([card.card_id for card in result], ["card-1", "card-2", "card-3"])

    def test_list_cards_returns_general_card_models(self):
        response = Mock()
        response.json.return_value = [{
            "id": "card-1",
            "idList": "list-1",
            "name": "Task",
            "desc": "Description",
            "due": None,
            "dueComplete": False,
            "closed": False,
            "members": [{"id": "member-1", "username": "apomen", "fullName": "Andres Pomen"}],
        }]

        with patch.object(trello, "_validate_list_board_id"):
            with patch.object(trello.requests, "get", return_value=response):
                result = trello.get_trello_cards_in_list("list-1")

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], trello.TrelloGeneralCard)
        self.assertEqual(result[0].assigned_user[0].username, "apomen")

    def test_list_cards_requests_assigned_users_in_same_trello_call(self):
        response = Mock()
        response.json.return_value = []

        with patch.object(trello, "_validate_list_board_id"):
            with patch.object(trello.requests, "get", return_value=response) as get:
                trello.get_trello_cards_in_list("list-1")

        params = get.call_args.kwargs["params"]
        self.assertEqual(params["members"], "true")
        self.assertEqual(params["member_fields"], "id,username,fullName,initials")
        self.assertIn("idMembers", params["fields"])

    def test_board_members_returns_assigned_user_models(self):
        response = Mock()
        response.json.return_value = [{
            "id": "member-1",
            "username": "apomen",
            "fullName": "Andres Pomen",
            "initials": "AP",
        }]

        with patch.object(trello, "api_key", "key"):
            with patch.object(trello, "api_token", "token"):
                with patch.object(trello.requests, "get", return_value=response) as get:
                    result = trello.get_trello_board_members()

        self.assertEqual(get.call_args.kwargs["params"]["fields"], "id,username,fullName,initials")
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], trello.TrelloAssignedUser)
        self.assertEqual(result[0].user_id, "member-1")

    def test_write_card_can_assign_users(self):
        response = Mock()
        response.json.return_value = {
            "id": "card-1",
            "idList": "list-1",
            "name": "Task",
            "desc": "Description",
            "idMembers": ["member-1", "member-2"],
        }

        with patch.object(trello, "_validate_list_board_id"):
            with patch.object(trello.requests, "post", return_value=response) as post:
                result = trello.write_trello_card_in_list(
                    list_id="list-1",
                    name="Task",
                    desc="Description",
                    assigned_user=" member-1, member-2,member-1 ",
                )

        params = post.call_args.kwargs["params"]
        self.assertEqual(params["idMembers"], "member-1,member-2")
        self.assertEqual(result.assigned_user[0].user_id, "member-1")

    def test_update_card_can_replace_or_clear_assigned_users(self):
        response = Mock()
        response.json.return_value = {
            "id": "card-1",
            "idList": "list-1",
            "name": "Task",
            "desc": "Description",
            "idMembers": [],
        }

        with patch.object(trello, "_validate_card_board_id") as validate_card:
            with patch.object(trello.requests, "put", return_value=response) as put:
                result = trello.update_trello_card(card_id="card-1", assigned_user="")

        validate_card.assert_called_once_with("card-1")
        params = put.call_args.kwargs["params"]
        self.assertEqual(params["idMembers"], "")
        self.assertEqual(result.assigned_user, [])


if __name__ == "__main__":
    unittest.main()
