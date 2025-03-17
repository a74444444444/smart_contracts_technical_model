from datastructures import SwapInstruction


class SwapAdapter:
    pool: str

    def doSwap(self, swap: SwapInstruction):
        ...

    def quoteSwap(self, swap: SwapInstruction) -> int:
        ...


class SwapRouter:
    whitelistedSwapAdapters: dict[SwapAdapter, bool]
    adaptersList: list[SwapAdapter]

    def swapViaAdapter(self, swap_adapter: SwapAdapter, swap: SwapInstruction):
        ...

    def swap(self, swap: SwapInstruction):
        ...

    def quote(self, swap_adapter: SwapAdapter, swap: SwapInstruction):
        ...

    def quoteBest(self, swap: SwapInstruction) -> int:
        quotes = []
        for adapter in self.adaptersList:
            quotes.append(adapter.quoteSwap(swap))
        return max(quotes)

