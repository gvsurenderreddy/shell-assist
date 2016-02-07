#!/usr/bin/env python

import sys
import random
import socket
import select
import threading


ENCODING = "utf-16"
BUFFER_SIZE = 4096
DELAY = 0.1
MAX_CONNECTIONS = 100


class ServerConnection:
	"""For server connection and transmission of data"""

	input_list = []
	channels = {}
	usernames = {}
	usernames_reverse = {} # useful for reverse lookup
	
	def __init__(self, host, port = 9876):
		self.host = host
		self.port = int(port)
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.bind((self.host, self.port))
		self.server.listen(MAX_CONNECTIONS)

	def listening_loop(self):
		print("Assist-Server starting...")
		print("Listening to connections...")
		self.input_list.append(self.server)
		while True:
			try:
				readlist, writelist, exceptlist = select.select(self.input_list, [], [], DELAY)
				for ready_server in readlist:
					if ready_server == self.server:
						self.on_accept()
						break
					self.data = ready_server.recv(BUFFER_SIZE)
					if len(self.data):
						self.on_recv(ready_server)
					else:
						self.on_close(ready_server)
						break
			except ConnectionRefusedError:
				print("Client has disconnected!")
			except Exception as e:
				print(e)
				break

	def generate_guestname(self):
		random.seed()
		return "Guest{}".format(random.randrange(100000, 1000000))

	def server_parse_recv_command(self, dest, line):
		line = line.strip()
		l_line = line.lower()

		if l_line.startswith("/setname ") or l_line.startswith("/setname\t"):
			# /setname command
			name = line[9:].lstrip()
			if name not in self.usernames and dest in self.usernames_reverse:
				# client attempting to change name
				self.usernames[name] = dest
				self.usernames_reverse[dest] = name
				old_name = self.usernames_reverse[dest]
				del self.usernames[old_name]
				dest.sendall(bytes("///nameack///{}".format(name), ENCODING))
				print("Client {} changed name to '{}'.".format(self.channels[dest], name))

			elif name not in self.usernames:
				# client choosing name upon connect
				self.usernames[name] = dest
				self.usernames_reverse[dest] = name
				dest.sendall(bytes("///nameack///{}".format(name), ENCODING))
				print("Client {} has identified as '{}'.".format(self.channels[dest], name))

			elif dest not in self.usernames_reverse:
				# name already taken, but generate guest name
				name = self.generate_guestname()
				self.usernames[name] = dest
				self.usernames_reverse[dest] = name
				dest.sendall(bytes("///nameguest///{}".format(name), ENCODING))
				print("Client {} force-changed name to '{}'.".format(self.channels[dest], name))

			else:
				# name already taken
				dest.sendall(bytes("///namedenied///{}".format(name), ENCODING))

		elif l_line == "///list///":
			output = "List of online users:"
			for user in self.usernames:
				output += "\n" + user
			dest.sendall(bytes(output, ENCODING))

		elif l_line.startswith("///listpattern///"):
			pass

		elif l_line.startswith("///chat///"):
			# for chat window
			parts = line.split("///")
			if parts[2] in self.usernames:
				self.usernames[parts[2]].sendall(bytes("///chat///{}///{}".format(
					self.usernames_reverse[dest], parts[3]), ENCODING))
			else:
				dest.sendall(bytes("///usernone///{}".format(parts[2]), ENCODING))

		elif l_line.startswith("/"):
			# unrecognized command
			dest.sendall(bytes("///error///unrecognized command.", ENCODING))

		else:
			# not a command
			print("{}{}".format(self.prompt(self.usernames_reverse[dest], self.channels[dest][0]), line))

	def on_accept(self):
		client_sock, client_addr = self.server.accept()
		self.input_list.append(client_sock)
		self.channels[client_sock] = client_addr
		print("Client {} has connected.".format(client_addr))
		client_sock.sendall(bytes("Welcome.", ENCODING))

	def on_recv(self, dest):
		self.data = self.data.decode(ENCODING)
		self.server_parse_recv_command(dest, self.data)

	def on_close(self, dest):
		print("Client {} has disconnected.".format(dest.getpeername()))
		name = self.usernames_reverse[dest]
		del self.usernames_reverse[dest]
		del self.usernames[name]
		self.input_list.remove(dest)
		del self.channels[dest]
		dest.close()

	def start_server(self):
		try:
			self.listening_loop()
		except KeyboardInterrupt:
			print("\nStopping server...")
			self.server.close()
			sys.exit(0)

	def prompt(self, name, addr):
		return "[{}@{}]> ".format(name, addr)


class ClientConnection:
	"""For client connection"""

	input_list = []
	
	def __init__(self, host, port = 9876, username = 'me'):
		self.listen_loop = True
		self.connect_loop = True
		self.host = host
		self.port = int(port)
		self.username = username
		self.mode = ["", ""] # the first is the mode ("", "chat", "shell" or "file") and the second is the target
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # create TCP socket
		self.input_list.append(self.sock)

	def listen_receive(self):
		readlist, writelist, exceptlist = select.select(self.input_list, [], [], DELAY)
		while self.listen_loop:
			if not self.sock:
				break
			for input_ready in readlist:
				if input_ready == self.sock:
					self.data = self.sock.recv(BUFFER_SIZE)
					self.client_parse_recv_command(self.data.decode(ENCODING))

	def send_name(self):
		self.sock.sendall(bytes("/setname {}".format(self.username), ENCODING))

	def prompt(self, name = ''):
		if not name:
			name = self.username
		return str(name) + "> "

	def client_parse_recv_command(self, line):
		line = line.strip()
		l_line = line.lower()

		if l_line.startswith("///error///"):
			print("Error: {}".format(line[11:]))

		elif l_line.startswith("///nameack///"):
			self.username = line[13:]
			print("{}Your name was set to '{}'.".format(self.prompt("Client"), self.username))

		elif l_line.startswith("///nameguest///"):
			self.username = line[15:]
			print("{}Your name was changed to '{}'.".format(self.prompt("Client"), self.username))

		elif l_line.startswith("///namedenied///"):
			print("{}Name already in use.".format(self.prompt("Server")))

		elif l_line.startswith("///chat///"):
			parts = line.split("///")
			print("{}{}".format(self.prompt(parts[2]), parts[3]))

		elif l_line.startswith("///usernone///"):
			print("{}User '{}' is not online.".format(self.prompt("Server"), line[15:]))

		elif line:
			print("{}{}".format(self.prompt("Server"), line))

	def client_parse_sent_command(self, sock, line):
		line = line.strip()
		l_line = line.lower()

		if l_line == "/exit" or l_line == "/quit":
			self.connect_loop = False

		elif l_line == "/list":
			line = "///list///"

		elif l_line.startswith("/list ") or l_line.startswith("/list\t"):
			args = line[6:].lstrip()
			line = "///listpattern///{}".format(args)

		elif l_line.startswith("/chat ") or l_line.startswith("/chat\t"):
			args = line[6:].lstrip()
			self.mode = ["chat", args]
			line = ""

		elif l_line.startswith("/shell ") or l_line.startswith("/shell\t"):
			args = line[7:].lstrip()
			pass

		elif l_line.startswith("/send ") or l_line.startswith("/send\t"):
			args = line[6:].lstrip()
			pass

		elif l_line == "/close":
			# close chat, shell or file sending
			self.mode = ["", ""]
			line = ""

		if line and self.connect_loop:
			if self.mode[0] == "chat" and not line.startswith("///"):
				appended_line = "///chat///{}///".format(self.mode[1]) + line
			else:
				appended_line = line
			sock.sendall(bytes(appended_line, ENCODING))

	def connect_to_server(self):
		try:
			print(self.prompt("Client") + "Starting...")
			self.sock.connect((self.host, self.port))
			self.listening_thread = threading.Thread(target=self.listen_receive)
			self.listening_thread.daemon = True
			self.listening_thread.start()
			print("{}Connected to server.".format(self.prompt("Client")))
			self.send_name()

			while self.connect_loop:
				if not self.sock:
					print(self.prompt("Client") + "Server disconnected.")
					break
				line = input()
				self.client_parse_sent_command(self.sock, line)

			print(self.prompt("Client") + "Disconnecting...")
			self.sock.close()
			self.listen_loop = False
			sys.exit(0)

		except ConnectionRefusedError:
			print(self.prompt("Client") + "Error: Assist-Server not available on this address and/or port!")
			self.listen_loop = False
			sys.exit(1)

		except KeyboardInterrupt:
			print("\n" + self.prompt("Client") + "Exiting...")
			self.sock.close()
			self.listen_loop = False
			sys.exit(0)

		except BrokenPipeError:
			print("{}Server closed the connection.".format(self.prompt("Client")))
			self.listen_loop = False
			sys.exit(1)

		except Exception as e:
			self.listen_loop = False
			print(e)
			sys.exit(1)
