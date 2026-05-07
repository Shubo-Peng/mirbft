# client.py
import grpc
import communication_pb2
import communication_pb2_grpc

class Node:
    def __init__(self, name, port):
        self.name = name
        self.port = port
        self.channel = grpc.insecure_channel(f'localhost:{port}')
        self.stub = communication_pb2_grpc.CommunicationServiceStub(self.channel)

    def send_message(self, target_port, content):
        message = communication_pb2.Message(sender=self.name, content=content)
        response = self.stub.SendMessage(message)
        print(f"Sent message to port {target_port}. Response: {response.content}")
