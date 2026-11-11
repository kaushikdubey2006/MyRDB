
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

        self.page_id = page_id

        self.header = PageHeader(page_id)

        # Complete 4096-byte page
        self.data = bytearray(PAGE_SIZE)

        # Store header
        self._write_header()

        # slot_id -> (offset, length)
        self.slots = []

        # Deleted slot IDs
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

    def _read_slots(self):
        """
        Reconstruct the slot directory from page bytes.

        Slots are stored backwards from the end of the page.
        A (0, 0) entry represents unused directory space.
        """

        self.slots = []
        self.deleted_slots = set()

        slot_id = 0

        while True:

            position = (
                PAGE_SIZE
                - ((slot_id + 1) * SLOT_SIZE)
            )

            if position < PAGE_HEADER_SIZE:
                raise ValueError(
                    "Slot directory exceeds page boundary"
                )

            slot_data = self.data[
                position:position + SLOT_SIZE
            ]

            offset, length = struct.unpack(
                SLOT_FORMAT,
                slot_data
            )

            # No more slots
            if offset == 0 and length == 0:
                break

            # Validate slot offset
            if offset < PAGE_HEADER_SIZE:
                raise ValueError(
                    "Invalid record offset in slot directory"
                )

            if offset >= PAGE_SIZE:
                raise ValueError(
                    "Record offset exceeds page boundary"
                )

            if offset + length > PAGE_SIZE:
                raise ValueError(
                    "Record exceeds page boundary"
                )

            self.slots.append(
                (offset, length)
            )

            # Length zero means deleted
            if length == 0:
                self.deleted_slots.add(slot_id)

            slot_id += 1

        # Check that records do not overlap the slot directory
        directory_start = self._slot_directory_start()

        for offset, length in self.slots:

            if length > 0 and offset + length > directory_start:
                raise ValueError(
                    "Record overlaps slot directory"
                )

        active_count = sum(
            1
            for offset, length in self.slots
            if length > 0
        )

        if active_count != self.header.record_count:
            raise ValueError(
                "Record count does not match slot directory"
            )

    # =========================
    # Free Space
    # =========================

    def calculate_free_space(self):

        record_end = PAGE_HEADER_SIZE

        for offset, length in self.slots:

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

        if not isinstance(record, Record):
            raise TypeError(
                "insert_record expects a Record object"
            )

        record_bytes = record.serialize()

        record_length = len(record_bytes)

        # Find a deleted slot to reuse
        reusable_slot = None

        for slot_id in sorted(self.deleted_slots):

            reusable_slot = slot_id
            break

        # Check available space
        required_space = record_length

        if reusable_slot is None:
            required_space += SLOT_SIZE

        if self.calculate_free_space() < required_space:

            raise ValueError(
                "Not enough free space in page"
            )

        # Find the end of active records
        record_offset = PAGE_HEADER_SIZE

        for offset, length in self.slots:

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

        # Reuse deleted slot
        if reusable_slot is not None:

            self.slots[reusable_slot] = (
                record_offset,
                record_length
            )

            self.deleted_slots.remove(
                reusable_slot
            )

            slot_id = reusable_slot

        else:

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

        old_offset, old_length = self.slots[slot_id]

        new_length = len(new_bytes)

        # Case 1: New record fits existing space
        if new_length <= old_length:

            self.data[
                old_offset:
                old_offset + new_length
            ] = new_bytes

            self.slots[slot_id] = (
                old_offset,
                new_length
            )

        # Case 2: New record needs more space
        else:

            # Temporarily mark old location as free
            self.slots[slot_id] = (
                old_offset,
                0
            )

            # Existing slot is reused, so no new SLOT_SIZE
            # is required.
            if self.calculate_free_space() < new_length:

                self.slots[slot_id] = (
                    old_offset,
                    old_length
                )

                raise ValueError(
                    "Not enough free space for update"
                )

            # Find the end of active records
            new_offset = PAGE_HEADER_SIZE

            for offset, length in self.slots:

                if length > 0:

                    new_offset = max(
                        new_offset,
                        offset + length
                    )

            # Write updated record
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

        offset, length = self.slots[slot_id]

        if length == 0:

            raise ValueError(
                "Record already deleted"
            )

        # Mark slot as deleted
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
    # Record Compaction
    # =========================

    def compact(self):
        """
        Reorganize active records into contiguous storage.

        Existing slot IDs are preserved so that record
        locations (page_id, slot_id) remain unchanged.
        """

        self.validate()

        free_space_before = self.calculate_free_space()

        # Preserve all active record bytes before rebuilding.
        active_records = {}

        for slot_id, (offset, length) in enumerate(self.slots):

            if length > 0:

                active_records[slot_id] = bytes(
                    self.data[offset:offset + length]
                )

        # Create a fresh page buffer.
        new_data = bytearray(PAGE_SIZE)

        new_slots = []
        current_offset = PAGE_HEADER_SIZE

        # Repack active records while preserving slot IDs.
        for slot_id, (old_offset, old_length) in enumerate(self.slots):

            if old_length == 0:

                # Preserve deleted slot for future reuse.
                new_slots.append(
                    (PAGE_HEADER_SIZE, 0)
                )

                continue

            record_bytes = active_records[slot_id]
            record_length = len(record_bytes)

            new_data[
                current_offset:current_offset + record_length
            ] = record_bytes

            new_slots.append(
                (current_offset, record_length)
            )

            current_offset += record_length

        # Replace old page data and slot directory.
        self.data = new_data
        self.slots = new_slots

        # Reconstruct deleted slot information.
        self.deleted_slots = {
            slot_id
            for slot_id, (_, length) in enumerate(self.slots)
            if length == 0
        }

        # Update metadata.
        self.header.free_space = self.calculate_free_space()

        self._write_slots()
        self._write_header()

        self.validate()

        # Return the additional contiguous free space.
        return (
            self.header.free_space - free_space_before
        )


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

        self.validate()

        offset = self.page_id * PAGE_SIZE

        file.seek(offset)

        file.write(self.data)

    # =========================
    # Page Read
    # =========================

    @classmethod
    def read_from_file(cls, file, page_id):

        offset = page_id * PAGE_SIZE

        file.seek(offset)

        data = file.read(PAGE_SIZE)

        if len(data) != PAGE_SIZE:

            raise ValueError(
                "Incomplete page read"
            )

        page = cls(page_id)

        page.data = bytearray(data)

        page._read_header()

        # Verify the requested page ID
        if page.header.page_id != page_id:

            raise ValueError(
                "Page ID mismatch"
            )

        # Reconstruct in-memory slot information
        page._read_slots()

        # Validate loaded page
        page.validate()

        return page

    # =========================
    # Validation
    # =========================

    def validate(self):

        if len(self.data) != PAGE_SIZE:

            raise ValueError(
                "Invalid page size"
            )

        header = PageHeader.unpack(
            self.data[:PAGE_HEADER_SIZE]
        )

        if header.magic != PAGE_MAGIC:

            raise ValueError(
                "Invalid page magic"
            )

        if header.version != FORMAT_VERSION:

            raise ValueError(
                "Unsupported page format version"
            )

        if header.page_id != self.page_id:

            raise ValueError(
                "Page ID mismatch"
            )

        if header.record_count != self.header.record_count:

            raise ValueError(
                "Record count mismatch"
            )

        if header.free_space != self.header.free_space:

            raise ValueError(
                "Free space metadata mismatch"
            )

        if header.record_count < 0:

            raise ValueError(
                "Invalid record count"
            )

        if self.header.free_space != self.calculate_free_space():

            raise ValueError(
                "Incorrect free space calculation"
            )

        return True


# =========================
# Chapter 3 and Persistence Tests
# =========================

if __name__ == "__main__":

    import tempfile

    print("=== MyRDB Page Engine Test ===")

    page = Page(0)

    print("\nInitial Free Space:")
    print(page.calculate_free_space())

    # INSERT
    slot1 = page.insert_record(
        Record([101, "Aman", 20])
    )

    slot2 = page.insert_record(
        Record([102, "Ravi", 21])
    )

    slot3 = page.insert_record(
        Record([103, "Rahul", 22])
    )

    print("\nInserted Slots:")
    print(slot1, slot2, slot3)

    print("\nRecord Count:")
    print(page.header.record_count)

    # READ
    print("\nRead Records:")

    print(page.read_record(slot1))
    print(page.read_record(slot2))
    print(page.read_record(slot3))

    # UPDATE
    page.update_record(
        slot2,
        Record([102, "Ravi", 25])
    )

    print("\nAfter Update:")
    print(page.read_record(slot2))

    # DELETE
    page.delete_record(slot1)

    print("\nAfter Delete:")
    print("Record Count:", page.header.record_count)

    try:
        page.read_record(slot1)

    except ValueError as error:
        print("Read deleted record:", error)

    # SLOT REUSE
    new_slot = page.insert_record(
        Record([104, "Neha", 23])
    )

    print("\nReused Slot:")
    print(new_slot)

    print("\nNew Record:")
    print(page.read_record(new_slot))

    # VALIDATION
    print("\nPage Validation:")
    print(page.validate())

    print("\nFinal Free Space:")
    print(page.calculate_free_space())

    # =========================
    # PERSISTENCE TEST
    # =========================

    print("\n=== Persistence Test ===")

    with tempfile.TemporaryFile(mode="w+b") as file:

        # Save page
        page.write_to_file(file)
        file.flush()

        print("\nPage written to file.")

        # Reload page from file
        loaded_page = Page.read_from_file(
            file,
            0
        )

        print("Page loaded successfully.")

        print("\nRestored Slots:")
        print(loaded_page.slots)

        print("\nRestored Deleted Slots:")
        print(loaded_page.deleted_slots)

        print("\nRestored Records:")

        for index in range(len(loaded_page.slots)):

            if index not in loaded_page.deleted_slots:

                print(
                    index,
                    loaded_page.read_record(index)
                )

        print("\nLoaded Page Validation:")
        print(loaded_page.validate())

        # Test operations after reload
        loaded_page.insert_record(
            Record([105, "Karan", 24])
        )

        print("\nRecord Inserted After Reload:")
        print(loaded_page.read_record(3))

    print("\n=== All Tests Completed ===")
