from datastructures import Message


class Messaging:
    last_message: Message

    def send_message(self, message: Message) -> None:
        self.last_message = message

class LayerZero(Messaging):
    def lzReceive(self, message: bytes):
        self._receive_message(message)

    def _receive_message(self, message: bytes):
        ...