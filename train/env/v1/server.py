# server.py
import grpc
from concurrent import futures
import communication_pb2
import communication_pb2_grpc

class CommunicationServicer(communication_pb2_grpc.CommunicationServiceServicer):
    def SendMessage(self, request, context):
        print(f"Received message from {request.sender}: {request.content}")
        return communication_pb2.Message(sender="Server", content=f"Received your message, {request.sender}")

def serve(port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    communication_pb2_grpc.add_CommunicationServiceServicer_to_server(CommunicationServicer(), server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"Server started on port {port}")
    server.wait_for_termination()
