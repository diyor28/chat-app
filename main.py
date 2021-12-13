import asyncio
import http.server
import json
import socketserver
import threading

import websockets
from websockets.legacy.server import WebSocketServerProtocol

from chat import Client, Chat

HTTP_PORT = 8000
WS_PORT = 8765


class Server:
	clients: dict[WebSocketServerProtocol, Client]

	def __init__(self):
		self.host = "localhost"
		self.port = WS_PORT
		self.clients = {}
		self.chat = Chat()

	async def run(self):
		async with websockets.serve(self.handler, self.host, self.port):
			await self.broadcast_messages()  # runs forever

	async def broadcast_messages(self):
		while True:
			# if not clients:
			await asyncio.sleep(0.5)
			clients = self.clients.copy()
			for websocket in clients.keys():
				try:
					if len(websocket.messages):
						message = await self.read(websocket)
						self.process_message(websocket, message)
				except websockets.ConnectionClosed as e:
					print(e)

	async def read(self, websocket: WebSocketServerProtocol):
		message = await websocket.recv()
		return json.loads(message)

	def process_message(self, websocket: WebSocketServerProtocol, message: dict):
		event, data = message['event'], message['data']
		if event == 'message':
			self.chat.message_to_person(data, self.clients[websocket])

		if event == 'fetch_users':
			self.chat.fetch_users(self.clients[websocket])

		if event == 'join':
			self.chat.client_joined(data, self.clients[websocket])

		if event == 'message_to_group':
			self.chat.message_to_group(data, self.clients[websocket])

		if event == 'create_group':
			self.chat.create_group(data, self.clients[websocket])

		if event == 'add_to_group':
			self.chat.add_to_group(data)

		if event == 'remove_from_group':
			self.chat.remove_from_group(data)

	async def handler(self, websocket: WebSocketServerProtocol):
		client = Client(websocket)
		self.clients[websocket] = client
		try:
			await websocket.wait_closed()
		finally:
			self.clients.pop(websocket)
			self.chat.client_disconnected(client)


class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
	def do_GET(self):
		if self.path == '/':
			self.path = 'index.html'
		return super().do_GET()


def run_http_server():
	handler_object = MyHttpRequestHandler

	my_server = socketserver.TCPServer(("", HTTP_PORT), handler_object)

	my_server.serve_forever()


def run_websocket_server():
	server = Server()
	asyncio.run(server.run())


if __name__ == "__main__":
	http_server = threading.Thread(target=run_http_server, daemon=True)
	websocket_server = threading.Thread(target=run_websocket_server, daemon=True)
	http_server.start()
	websocket_server.start()
	print("Open http://localhost:8000 in your browser to start chatting")
	http_server.join()
	websocket_server.join()

# Create an object of the above class
