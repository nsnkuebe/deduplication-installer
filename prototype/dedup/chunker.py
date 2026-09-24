class FixedChunker:
    def __init__(self, size: int):
        if size <= 0:
            raise ValueError("chunk size must be positive")
        self.size = size

    def split(self, data: bytes) -> list[tuple[int, int]]:
        return [(offset, min(self.size, len(data) - offset))
                for offset in range(0, len(data), self.size)]