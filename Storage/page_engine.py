import struct

from config import PAGE_SIZE, PAGE_MAGIC, FORMAT_VERSION


# =========================
# Page Header Configuration
# =========================

PAGE_HEADER_FORMAT = "<4sHIHI"
PAGE_HEADER_SIZE = struct.calcsize(PAGE_HEADER_FORMAT)


# =========================
# Page Header
# =========================

class PageHeader:
    def __init__(
        self,
        page_id,
        record_count=0,
        free_space=PAGE_SIZE - PAGE_HEADER_SIZE
    ):
        self.magic = PAGE_MAGIC
        self.version = FORMAT_VERSION
        self.page_id = page_id
        self.record_count = record_count
        self.free_space = free_space

    def pack(self):
        return struct.pack(
            PAGE_HEADER_FORMAT,
            self.magic,
            self.version,
            self.page_id,
            self.record_count,
            self.free_space
        )

    @classmethod
    def unpack(cls, data):
        values = struct.unpack(PAGE_HEADER_FORMAT, data)

        header = cls(
            page_id=values[2],
            record_count=values[3],
            free_space=values[4]
        )

        header.magic = values[0]
        header.version = values[1]

        return header


# =========================
# Page
# =========================

class Page:
    def __init__(self, page_id):
        self.header = PageHeader(page_id)
        self.data = bytearray(PAGE_SIZE)

        self.data[:PAGE_HEADER_SIZE] = self.header.pack()

    def write_to_file(self, file):
        offset = self.header.page_id * PAGE_SIZE

        file.seek(offset)
        file.write(self.data)

    @classmethod
    def read_from_file(cls, file, page_id):
        offset = page_id * PAGE_SIZE

        file.seek(offset)
        data = file.read(PAGE_SIZE)

        if len(data) != PAGE_SIZE:
            raise ValueError("Incomplete page read")

        page = cls(page_id)
        page.data = bytearray(data)

        return page

    def validate(self):
        if len(self.data) != PAGE_SIZE:
            raise ValueError("Invalid page size")

        header_data = self.data[:PAGE_HEADER_SIZE]
        header = PageHeader.unpack(header_data)

        if header.magic != PAGE_MAGIC:
            raise ValueError("Invalid page magic")

        if header.version != FORMAT_VERSION:
            raise ValueError("Unsupported page format version")

        if header.page_id != self.header.page_id:
            raise ValueError("Page ID mismatch")

        return True