
from pathlib import Path

from config import PAGE_SIZE
from storage.page_engine import (
    Page,
    Record,
    PAGE_HEADER_SIZE,
    SLOT_SIZE
)


class PageManager:

    def __init__(self, database_file):

        self.database_file = Path(database_file)

        self.database_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.pages = {}
        self.next_page_id = 0

        # page_id -> contiguous free space
        self.free_space_map = {}

        # Pages containing no active records.
        self.reusable_page_ids = set()

        self._load_existing_pages()

    # =========================
    # Load Existing Pages
    # =========================

    def _load_existing_pages(self):

        if not self.database_file.exists():
            return

        file_size = self.database_file.stat().st_size

        if file_size % PAGE_SIZE != 0:
            raise ValueError(
                "Database file contains incomplete pages"
            )

        total_pages = file_size // PAGE_SIZE

        with open(self.database_file, "rb") as file:

            for page_id in range(total_pages):

                page = Page.read_from_file(
                    file,
                    page_id
                )

                self.pages[page_id] = page

                self.free_space_map[page_id] = (
                    page.calculate_free_space()
                )

                if page.header.record_count == 0:
                    self.reusable_page_ids.add(page_id)

        self.next_page_id = total_pages

    # =========================
    # Allocate New Page
    # =========================

    def allocate_page(self):

        page_id = self.next_page_id

        page = Page(page_id)

        self.pages[page_id] = page

        self.next_page_id += 1

        self.save_page(page_id)

        return page

    # =========================
    # Get Page
    # =========================

    def get_page(self, page_id):

        if page_id not in self.pages:
            raise ValueError(
                f"Page {page_id} does not exist"
            )

        return self.pages[page_id]

    # =========================
    # Save Page
    # =========================

    def save_page(self, page_id):

        page = self.get_page(page_id)

        mode = (
            "r+b"
            if self.database_file.exists()
            else "w+b"
        )

        with open(self.database_file, mode) as file:

            page.write_to_file(file)

            file.flush()

        # Update free-space information.
        self.free_space_map[page_id] = (
            page.calculate_free_space()
        )

        # Update reusable-page information.
        if page.header.record_count == 0:

            self.reusable_page_ids.add(page_id)

        else:

            self.reusable_page_ids.discard(page_id)

    # =========================
    # Find Page With Free Space
    # =========================

    def find_page_with_free_space(
        self,
        required_space,
        exclude_page_ids=None
    ):

        if (
            not isinstance(required_space, int)
            or isinstance(required_space, bool)
            or required_space < 0
        ):
            raise ValueError(
                "Required space must be a non-negative integer"
            )

        if exclude_page_ids is None:
            exclude_page_ids = set()

        for page_id in sorted(self.free_space_map):

            if page_id in exclude_page_ids:
                continue

            available_space = self.free_space_map[page_id]

            if available_space >= required_space:

                return self.get_page(page_id)

        return None

    # =========================
    # Get Page Free Space
    # =========================

    def get_page_free_space(self, page_id):

        if page_id not in self.free_space_map:
            raise ValueError(
                f"Page {page_id} does not exist"
            )

        return self.free_space_map[page_id]

    # =========================
    # Get Complete Free Space Map
    # =========================

    def get_free_space_map(self):

        return self.free_space_map.copy()

    # =========================
    # Rebuild Free Space Map
    # =========================

    def rebuild_free_space_map(self):

        rebuilt_map = {}

        for page_id in sorted(self.pages):

            page = self.pages[page_id]

            rebuilt_map[page_id] = (
                page.calculate_free_space()
            )

        self.free_space_map = rebuilt_map

        return self.free_space_map.copy()

    # =========================
    # Validate Free Space Map
    # =========================

    def validate_free_space_map(self):

        if set(self.free_space_map) != set(self.pages):

            raise ValueError(
                "Free space map contains missing or extra pages"
            )

        for page_id in sorted(self.pages):

            actual_space = (
                self.pages[page_id].calculate_free_space()
            )

            tracked_space = self.free_space_map[page_id]

            if tracked_space != actual_space:

                raise ValueError(
                    f"Free space mismatch on Page {page_id}: "
                    f"tracked={tracked_space}, "
                    f"actual={actual_space}"
                )

        return True

    # =========================
    # Get Reusable Pages
    # =========================

    def get_reusable_pages(self):

        return sorted(self.reusable_page_ids)

    # =========================
    # Rebuild Reusable Pages
    # =========================

    def rebuild_reusable_pages(self):

        self.reusable_page_ids = {
            page_id
            for page_id, page in self.pages.items()
            if page.header.record_count == 0
        }

        return self.get_reusable_pages()

    # =========================
    # Validate Reusable Pages
    # =========================

    def validate_reusable_pages(self):

        expected_pages = {
            page_id
            for page_id, page in self.pages.items()
            if page.header.record_count == 0
        }

        if self.reusable_page_ids != expected_pages:

            raise ValueError(
                "Reusable page tracking mismatch"
            )

        return True

    # =========================
    # Reuse Empty Page
    # =========================

    def reuse_empty_page(self):

        if not self.reusable_page_ids:
            return None

        page_id = min(self.reusable_page_ids)

        # Reset page contents while preserving page ID.
        page = Page(page_id)

        self.pages[page_id] = page

        self.save_page(page_id)

        return page

    # =========================
    # Insert Record
    # =========================

    def insert_record(self, record):

        if not isinstance(record, Record):
            raise TypeError(
                "insert_record expects a Record object"
            )

        record_size = len(record.serialize())

        required_space = record_size + SLOT_SIZE

        # Ensure record fits on a completely fresh page.
        maximum_record_size = (
            PAGE_SIZE - PAGE_HEADER_SIZE - SLOT_SIZE
        )

        if record_size > maximum_record_size:

            raise ValueError(
                "Record is too large to fit in a page"
            )

        # First search non-empty pages.
        page = self.find_page_with_free_space(
            required_space,
            exclude_page_ids=self.reusable_page_ids
        )

        # If no existing page fits, reuse an empty page.
        if page is None:
            page = self.reuse_empty_page()

        # Allocate a new page only if reuse is unavailable.
        if page is None:
            page = self.allocate_page()

        slot_id = page.insert_record(record)

        page_id = page.header.page_id

        self.save_page(page_id)

        return page_id, slot_id

    # =========================
    # Read Record
    # =========================

    def read_record(self, page_id, slot_id):

        page = self.get_page(page_id)

        return page.read_record(slot_id)

    # =========================
    # Update Record
    # =========================

    def update_record(self, page_id, slot_id, record):

        if not isinstance(record, Record):
            raise TypeError(
                "update_record expects a Record object"
            )

        old_page = self.get_page(page_id)

        # First try updating on the original page.
        try:

            old_page.update_record(
                slot_id,
                record
            )

            self.save_page(page_id)

            return page_id, slot_id

        except ValueError as error:

            if str(error) != "Not enough free space for update":
                raise

        # Original page does not have enough space.
        record_size = len(record.serialize())

        required_space = record_size + SLOT_SIZE

        maximum_record_size = (
            PAGE_SIZE - PAGE_HEADER_SIZE - SLOT_SIZE
        )

        if record_size > maximum_record_size:

            raise ValueError(
                "Record is too large to fit in a page"
            )

        new_page = self.find_page_with_free_space(
            required_space,
            exclude_page_ids={page_id} | self.reusable_page_ids
        )

        if new_page is None:
            new_page = self.reuse_empty_page()

        if new_page is None:
            new_page = self.allocate_page()

        # Insert updated record on another page.
        new_slot_id = new_page.insert_record(record)

        new_page_id = new_page.header.page_id

        self.save_page(new_page_id)

        try:

            # Delete old record after saving new record.
            old_page.delete_record(slot_id)

            self.save_page(page_id)

        except Exception:

            # Best-effort cleanup.
            try:

                new_page.delete_record(new_slot_id)

                self.save_page(new_page_id)

            except Exception:
                pass

            raise

        return new_page_id, new_slot_id

    # =========================
    # Delete Record
    # =========================

    def delete_record(self, page_id, slot_id):

        page = self.get_page(page_id)

        page.delete_record(slot_id)

        self.save_page(page_id)

    # =========================
    # Compact Page
    # =========================

    def compact_page(self, page_id):

        page = self.get_page(page_id)

        reclaimed_space = page.compact()

        self.save_page(page_id)

        return reclaimed_space

    # =========================
    # Compact All Pages
    # =========================

    def compact_all_pages(self):

        total_reclaimed = 0

        for page_id in sorted(self.pages):

            total_reclaimed += self.compact_page(page_id)

        return total_reclaimed

    # =========================
    # Save All Pages
    # =========================

    def save_all_pages(self):

        for page_id in sorted(self.pages):
            self.save_page(page_id)

    # =========================
    # Page Information
    # =========================

    def get_page_count(self):

        return len(self.pages)

    def get_all_page_ids(self):

        return sorted(self.pages)


# =========================
# Page Manager Test
# =========================

if __name__ == "__main__":

    import tempfile

    print("=== MyRDB Page Manager Test ===")

    with tempfile.TemporaryDirectory() as temp_dir:

        database_file = Path(temp_dir) / "test.db"

        manager = PageManager(database_file)

        # INSERT
        location1 = manager.insert_record(
            Record([101, "Aman", 20])
        )

        location2 = manager.insert_record(
            Record([102, "Ravi", 21])
        )

        location3 = manager.insert_record(
            Record([103, "Rahul", 22])
        )

        print("\nInserted Record Locations:")
        print(location1)
        print(location2)
        print(location3)

        print("\nTotal Pages:")
        print(manager.get_page_count())

        # READ
        print("\nRead Record:")
        print(manager.read_record(*location1))

        # UPDATE
        updated_location = manager.update_record(
            *location2,
            Record([102, "Ravi", 25])
        )

        print("\nAfter Update:")
        print(manager.read_record(*updated_location))

        # DELETE
        manager.delete_record(*location3)

        print("\nAfter Delete:")

        try:
            manager.read_record(*location3)

        except ValueError as error:
            print(error)

        # FREE SPACE MAP
        print("\nFree Space Map:")
        print(manager.get_free_space_map())

        # REUSABLE PAGES
        print("\nReusable Pages:")
        print(manager.get_reusable_pages())

        # VALIDATION
        print("\nFree Space Map Validation:")
        print(manager.validate_free_space_map())

        print("\nReusable Page Validation:")
        print(manager.validate_reusable_pages())

        # RELOAD DATABASE
        print("\n=== Persistence Test ===")

        manager2 = PageManager(database_file)

        print("Recovered Page IDs:")
        print(manager2.get_all_page_ids())

        print("Recovered Free Space Map:")
        print(manager2.get_free_space_map())

        print("Recovered Reusable Pages:")
        print(manager2.get_reusable_pages())

        print("Recovered Record:")
        print(manager2.read_record(*location1))

        print("\nRecovered Map Validation:")
        print(manager2.validate_free_space_map())

        print("\nRecovered Reusable Page Validation:")
        print(manager2.validate_reusable_pages())

        print("\n=== Page Manager Test Complete ===")
