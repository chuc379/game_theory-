import unittest

from src.modules.room.controller.room_controller import RoomController
from src.modules.room.session_policy import SESSION_MODE_SINGLE_LINK
from src.shared.constants import ROOM_CODE_LENGTH


class FakeRoomRepository:
    def __init__(self):
        self.rooms = {}

    async def room_exists(self, room_id):
        return room_id in self.rooms

    async def save_info(self, room_id, info):
        self.rooms[room_id] = dict(info)

    async def find_info(self, room_id):
        return self.rooms.get(room_id)

    async def get_all_rooms(self):
        return list(self.rooms.values())

    async def delete_room(self, room_id):
        self.rooms.pop(room_id, None)
        return True

    async def get_current_round(self, room_id):
        return 0


class RoomControllerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.repo = FakeRoomRepository()
        self.controller = RoomController(self.repo)

    async def test_create_room_generates_the_id_on_the_server(self):
        result = await self.controller.create_room(
            config={"session_mode": SESSION_MODE_SINGLE_LINK},
            owner_mc="mc",
        )
        self.assertTrue(result["success"])
        room = result["room"]
        self.assertEqual(len(room["room_id"]), ROOM_CODE_LENGTH)
        self.assertEqual(room["owner_mc"], "mc")
        self.assertEqual(room["config"]["session_mode"], SESSION_MODE_SINGLE_LINK)

    async def test_created_rooms_have_unique_ids(self):
        ids = set()
        for _ in range(5):
            result = await self.controller.create_room(owner_mc="mc")
            ids.add(result["room"]["room_id"])
        self.assertEqual(len(ids), 5)

    async def test_update_room_merges_partial_config(self):
        created = await self.controller.create_room(
            config={"max_player_links": 4}, owner_mc="mc"
        )
        room_id = created["room"]["room_id"]

        updated = await self.controller.update_room(
            room_id, {"session_mode": SESSION_MODE_SINGLE_LINK}, "mc"
        )
        self.assertTrue(updated["success"])
        self.assertEqual(
            updated["room"]["config"]["session_mode"], SESSION_MODE_SINGLE_LINK
        )
        # The untouched field survives a partial patch.
        self.assertEqual(updated["room"]["config"]["max_player_links"], 4)

    async def test_update_and_delete_reject_a_different_mc(self):
        created = await self.controller.create_room(owner_mc="mc-a")
        room_id = created["room"]["room_id"]

        update = await self.controller.update_room(
            room_id, {"max_player_links": 2}, "mc-b"
        )
        self.assertFalse(update["success"])
        delete = await self.controller.delete_room(room_id, "mc-b")
        self.assertFalse(delete["success"])

    async def test_delete_room_removes_it_from_the_listing(self):
        created = await self.controller.create_room(owner_mc="mc")
        room_id = created["room"]["room_id"]

        deleted = await self.controller.delete_room(room_id, "mc")
        self.assertTrue(deleted["success"])
        self.assertEqual(await self.controller.list_public_rooms(), [])


if __name__ == "__main__":
    unittest.main()
