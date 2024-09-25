import socket

# Step 1: Set up a basic server to receive data (e.g., from Interlocutor A or B)
def start_server(host='0.0.0.0', port=5000):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Server listening on {host}:{port}")
    conn, addr = server_socket.accept()
    print(f"Connection established with {addr}")
    data = conn.recv(1024)
    print(f"Received data: {data.decode()}")
    conn.close()
    server_socket.close()

# Start server (run this and have external clients communicate with this server)
start_server()