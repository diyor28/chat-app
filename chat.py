import asyncio
import json
import uuid

from websockets.legacy.server import WebSocketServerProtocol


class WebSocketWrapper:
	def __init__(self, websocket: WebSocketServerProtocol):
		self.websocket = websocket

	async def recv(self):
		return await self.websocket.recv()

	async def emit(self, event, payload):
		message = json.dumps({"event": event, "data": payload})
		return await self.websocket.send(message)


class Client:
	def __init__(self, websocket: WebSocketServerProtocol, name: str = ""):
		self.websocket = WebSocketWrapper(websocket)
		self.id = str(uuid.uuid4())
		self.name = name

	def send(self, sender_id: str, message: str):
		asyncio.create_task(self.websocket.emit("message", {"message": message, "sender_id": sender_id}))


class Group:
	def __init__(self, owner: Client, name: str = ""):
		self.owner = owner
		self.id = str(uuid.uuid4())
		self.name = name
		self.members: set[Client] = set()

	def send(self, sender_id: str, message):
		for member in self.members:
			member.send(sender_id, message)

	def add_member(self, client: Client):
		self.members.add(client)

	def remove_member(self, client: Client):
		self.members.remove(client)


class Chat:
	groups: dict[str, Group]
	clients: dict[str, Client]

	def __init__(self):
		self.groups = {}
		self.clients = {}

	def client_joined(self, data: dict, client: Client):
		print('Client joined')
		client.name = data['name']
		self.clients[client.id] = client
		for member in self.clients.values():
			asyncio.create_task(member.websocket.emit("joined", {"id": client.id, "name": client.name}))
		return client

	def client_disconnected(self, client: Client):
		print('Client disconnected')
		self.clients.pop(client.id, None)
		for member in self.clients.values():
			asyncio.create_task(member.websocket.emit("disconnected", {"id": client.id, "name": client.name}))

	def fetch_users(self, sender: Client):
		result = []
		for client in self.clients.values():
			if client.id == sender.id:
				continue
			result.append({"id": client.id, "name": client.name})
		asyncio.create_task(sender.websocket.emit("fetched_users", result))

	def create_group(self, data: dict, owner: Client):
		group = Group(owner=owner, name=data["group_name"])
		self.groups[group.id] = group
		asyncio.create_task(owner.websocket.emit("group_created", {"id": group.id}))

	def message_to_person(self, data: dict, sender: Client):
		client_id, message = data["client_id"], data["message"]
		self.clients[client_id].send(sender.id, message)

	def message_to_group(self, data: dict, sender: Client):
		group_id, message = data["group_id"], data["message"]
		group = self.groups[group_id]
		group.send(sender.id, message)

	def add_to_group(self, data: dict):
		client = self.clients[data["client_id"]]
		group = self.groups[data["group_id"]]
		group.add_member(client)

	def remove_from_group(self, data: dict):
		client = self.clients[data["client_id"]]
		group = self.groups[data["group_id"]]
		group.remove_member(client)
