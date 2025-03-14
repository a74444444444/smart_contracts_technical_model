from datastructures import Message


class Messaging:
    def send_message(self, message: Message) -> None:
        ...

class LayerZero(Messaging):
    def lzReceive(self, message: bytes):
        self._receive_message(message)

    def _receive_message(self, message: bytes):
        ...