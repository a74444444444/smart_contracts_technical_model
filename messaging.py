from datastructures import Message


class Messaging:
    def send_message(self, message: Message) -> None:
        ...

class LayerZero(Messaging):
    def lzReceive(self):
        ...