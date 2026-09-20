import struct

from config import PAGE_SIZE, PAGE_MAGIC, FORMAT_VERSION


# =========================
# Page Header Configuration
# =========================

PAGE_HEADER_FORMAT = "<4sHIHI"
PAGE_HEADER_SIZE = struct.calcsize(PAGE_HEADER_FORMAT)

# Each slot stores:
# Offset + Length
SLOT_FORMAT = "<HH"
SLOT_SIZE = struct.calcsize(SLOT_FORMAT)


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

        values = struct.unpack(
            PAGE_HEADER_FORMAT,
            data
        )

        header = cls(
            page_id=values[2],
            record_count=values[3],
            free_space=values[4]
        )

        header.magic = values[0]
        header.version = values[1]

        return header


# =========================
# Record
# =========================

class Record:

    def __init__(self, values):
        self.values = values

    def serialize(self):
        """
        Convert record values into bytes.

        Example:
        [101, "Aman", 20]
        becomes:
        b"101|Aman|20"
        """

        data = "|".join(
            str(value)
            for value in self.values
        )

        return data.encode("utf-8")

    @classmethod
    def deserialize(cls, data):
        """
        Convert record bytes back into a Record.
        """

        text = data.decode("utf-8")

        values = text.split("|")

        return cls(values)

    def __repr__(self):
        return f"Record({self.values})"


# =========================
# Page
# =========================

class Page:

    def __init__(self, page_id):

        self.header = PageHeader(page_id)

        # Complete 4096-byte page
        self.data = bytearray(PAGE_SIZE)

        # Store header
        self._write_header()

        # Slot directory is maintained in memory.
        #
        # Each entry:
        # slot_id -> (offset, length)
        self.slots = []

        # Tracks deleted/reusable slots
        self.deleted_slots = set()

    # =========================
    # Header Helpers
    # =========================

    def _write_header(self):

        self.data[:PAGE_HEADER_SIZE] = self.header.pack()

    def _read_header(self):

        header_data = self.data[:PAGE_HEADER_SIZE]

        self.header = PageHeader.unpack(
            header_data
        )

    # =========================
    # Slot Directory
    # =========================

    def _slot_directory_start(self):

        return PAGE_SIZE - (
            len(self.slots) * SLOT_SIZE
        )

    def _write_slots(self):

        # Clear existing slot directory area
        start = self._slot_directory_start()

        # Write each slot
        for slot_id, slot in enumerate(self.slots):

            offset, length = slot

            position = (
                PAGE_SIZE
                - ((slot_id + 1) * SLOT_SIZE)
            )

            self.data[position:position + SLOT_SIZE] = (
                struct.pack(
                    SLOT_FORMAT,
                    offset,
                    length
                )
            )

    # =========================
    # Free Space
    # =========================

    def calculate_free_space(self):

        record_end = PAGE_HEADER_SIZE

        for slot in self.slots:

            offset, length = slot

            if length > 0:
                record_end = max(
                    record_end,
                    offset + length
                )

        slot_space = len(self.slots) * SLOT_SIZE

        free_space = (
            PAGE_SIZE
            - record_end
            - slot_space
        )

        return max(0, free_space)

    # =========================
    # Insert
    # =========================

    def insert_record(self, record):

        if isinstance(record, Record):
            record_bytes = record.serialize()
        else:
            raise TypeError(
                "insert_record expects a Record object"
            )

        record_length = len(record_bytes)

        # Check whether a deleted slot can be reused
        reusable_slot = None

        for slot_id in sorted(self.deleted_slots):

            old_offset, old_length = self.slots[slot_id]

            if old_length >= record_length:

                reusable_slot = slot_id
                break

        # =========================
        # Reuse Deleted Slot
        # =========================

        if reusable_slot is not None:

            old_offset, old_length = (
                self.slots[reusable_slot]
            )

            self.data[
                old_offset:
                old_offset + record_length
            ] = record_bytes

            self.slots[reusable_slot] = (
                old_offset,
                record_length
            )

            self.deleted_slots.remove(
                reusable_slot
            )

            self.header.record_count += 1

            self.header.free_space = (
                self.calculate_free_space()
            )

            self._write_slots()
            self._write_header()

            return reusable_slot

        # =========================
        # New Slot
        # =========================

        required_space = (
            record_length + SLOT_SIZE
        )

        if self.calculate_free_space() < required_space:

            raise ValueError(
                "Not enough free space in page"
            )

        # Find record offset
        record_offset = PAGE_HEADER_SIZE

        for slot in self.slots:

            offset, length = slot

            if length > 0:
                record_offset = max(
                    record_offset,
                    offset + length
                )

        # Write record bytes
        self.data[
            record_offset:
            record_offset + record_length
        ] = record_bytes

        # Add slot
        self.slots.append(
            (
                record_offset,
                record_length
            )
        )

        slot_id = len(self.slots) - 1

        self.header.record_count += 1

        self.header.free_space = (
            self.calculate_free_space()
        )

        self._write_slots()
        self._write_header()

        return slot_id

    # =========================
    # Read
    # =========================

    def read_record(self, slot_id):

        self._validate_slot_id(slot_id)

        offset, length = self.slots[slot_id]

        # Deleted slot
        if length == 0:
            raise ValueError(
                "Record has been deleted"
            )

        record_bytes = bytes(
            self.data[
                offset:
                offset + length
            ]
        )

        return Record.deserialize(
            record_bytes
        )

    # =========================
    # Update
    # =========================

    def update_record(self, slot_id, record):

        self._validate_slot_id(slot_id)

        if slot_id in self.deleted_slots:
            raise ValueError(
                "Cannot update deleted record"
            )

        if not isinstance(record, Record):
            raise TypeError(
                "update_record expects a Record object"
            )

        new_bytes = record.serialize()

        old_offset, old_length = (
            self.slots[slot_id]
        )

        new_length = len(new_bytes)

        # =========================
        # Case 1:
        # New record fits old space
        # =========================

        if new_length <= old_length:

            self.data[
                old_offset:
                old_offset + new_length
            ] = new_bytes

            self.slots[slot_id] = (
                old_offset,
                new_length
            )

        # =========================
        # Case 2:
        # New record is larger
        # =========================

        else:

            # Temporarily free old slot
            self.slots[slot_id] = (
                old_offset,
                0
            )

            required_space = (
                new_length
                + SLOT_SIZE
            )

            if self.calculate_free_space() < required_space:

                # Restore original slot
                self.slots[slot_id] = (
                    old_offset,
                    old_length
                )

                raise ValueError(
                    "Not enough free space for update"
                )

            # Find new location
            new_offset = PAGE_HEADER_SIZE

            for index, slot in enumerate(self.slots):

                offset, length = slot

                if length > 0:
                    new_offset = max(
                        new_offset,
                        offset + length
                    )

            # Store new record
            self.data[
                new_offset:
                new_offset + new_length
            ] = new_bytes

            self.slots[slot_id] = (
                new_offset,
                new_length
            )

        self.header.free_space = (
            self.calculate_free_space()
        )

        self._write_slots()
        self._write_header()

    # =========================
    # Delete
    # =========================

    def delete_record(self, slot_id):

        self._validate_slot_id(slot_id)

        offset, length = (
            self.slots[slot_id]
        )

        if length == 0:
            raise ValueError(
                "Record already deleted"
            )

        # Mark slot as deleted.
        #
        # We keep the offset but set
        # length to zero.
        self.slots[slot_id] = (
            offset,
            0
        )

        self.deleted_slots.add(
            slot_id
        )

        self.header.record_count -= 1

        self.header.free_space = (
            self.calculate_free_space()
        )

        self._write_slots()
        self._write_header()

    # =========================
    # Slot Validation
    # =========================

    def _validate_slot_id(self, slot_id):

        if not isinstance(slot_id, int):
            raise TypeError(
                "Slot ID must be an integer"
            )

        if slot_id < 0 or slot_id >= len(self.slots):

            raise ValueError(
                "Invalid Slot ID"
            )

    # =========================
    # Page Write
    # =========================

    def write_to_file(self, file):

        offset = (
            self.header.page_id
            * PAGE_SIZE
        )

        file.seek(offset)

        file.write(self.data)

    # =========================
    # Page Read
    # =========================

    @classmethod
    def read_from_file(cls, file, page_id):

        offset = (
            page_id
            * PAGE_SIZE
        )

        file.seek(offset)

        data = file.read(
            PAGE_SIZE
        )

        if len(data) != PAGE_SIZE:

            raise ValueError(
                "Incomplete page read"
            )

        page = cls(page_id)

        page.data = bytearray(data)

        page._read_header()

        return page

    # =========================
    # Validation
    # =========================

    def validate(self):

        if len(self.data) != PAGE_SIZE:

            raise ValueError(
                "Invalid page size"
            )

        header_data = (
            self.data[:PAGE_HEADER_SIZE]
        )

        header = PageHeader.unpack(
            header_data
        )

        if header.magic != PAGE_MAGIC:

            raise ValueError(
                "Invalid page magic"
            )

        if header.version != FORMAT_VERSION:

            raise ValueError(
                "Unsupported page format version"
            )

        if (
            header.page_id
            != self.header.page_id
        ):

            raise ValueError(
                "Page ID mismatch"
            )

        return True


# =========================
# Chapter 3 Test
# =========================

if __name__ == "__main__":

    print("=== MyRDB Chapter 3 Test ===")

    # Create page
    page = Page(0)

    print("\nInitial Free Space:")
    print(page.calculate_free_space())

    # =========================
    # INSERT
    # =========================

    record1 = Record(
        [101, "Aman", 20]
    )

    record2 = Record(
        [102, "Ravi", 21]
    )

    record3 = Record(
        [103, "Rahul", 22]
    )

    slot1 = page.insert_record(
        record1
    )

    slot2 = page.insert_record(
        record2
    )

    slot3 = page.insert_record(
        record3
    )

    print("\nInserted Slots:")
    print(slot1, slot2, slot3)

    print("\nRecord Count:")
    print(page.header.record_count)

    # =========================
    # READ
    # =========================

    print("\nRead Records:")

    print(
        page.read_record(slot1)
    )

    print(
        page.read_record(slot2)
    )

    print(
        page.read_record(slot3)
    )

    # =========================
    # UPDATE
    # =========================

    page.update_record(
        slot2,
        Record(
            [102, "Ravi", 25]
        )
    )

    print("\nAfter Update:")

    print(
        page.read_record(slot2)
    )

    # =========================
    # DELETE
    # =========================

    page.delete_record(
        slot1
    )

    print("\nAfter Delete:")

    print(
        "Record Count:",
        page.header.record_count
    )

    try:

        page.read_record(slot1)

    except ValueError as error:

        print(
            "Read deleted record:",
            error
        )

    # =========================
    # SLOT REUSE
    # =========================

    new_slot = page.insert_record(
        Record(
            [104, "Neha", 23]
        )
    )

    print("\nNew Record Slot:")
    print(new_slot)

    print("\nNew Record:")

    print(
        page.read_record(new_slot)
    )

    # =========================
    # VALIDATION
    # =========================

    print("\nPage Validation:")

    print(
        page.validate()
    )

    print("\nFinal Free Space:")

    print(
        page.calculate_free_space()
    )

    print("\n=== Chapter 3 Test Complete ===")