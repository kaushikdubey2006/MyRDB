
from pathlib import Path

from config import PAGE_SIZE
from storage.page_engine import Page, Record


class PageManager:

    def __init__(self, database_file):

        self.database_file = Path(database_file)

        self.database_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.pages = {}
        self.next_page_id = 0

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

    # =========================
    # Find Page With Free Space
    # =========================

    def find_page_with_free_space(
        self,
        required_space,
        exclude_page_ids=None
    ):

        if exclude_page_ids is None:
            exclude_page_ids = set()

        for page_id in sorted(self.pages):

            if page_id in exclude_page_ids:
                continue

            page = self.pages[page_id]

            if page.calculate_free_space() >= required_space:
                return page

        return None

    # =========================
    # Insert Record
    # =========================

    def insert_record(self, record):

        if not isinstance(record, Record):
            raise TypeError(
                "insert_record expects a Record object"
            )

        record_size = len(record.serialize())

        required_space = record_size + 4

        page = self.find_page_with_free_space(
            required_space
        )

        if page is None:
            page = self.allocate_page()

        slot_id = page.insert_record(record)

        self.save_page(page.header.page_id)

        return page.header.page_id, slot_id

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
        # Find another page, excluding the original page.

        record_size = len(record.serialize())
        required_space = record_size + 4

        new_page = self.find_page_with_free_space(
            required_space,
            exclude_page_ids={page_id}
        )

        if new_page is None:
            new_page = self.allocate_page()

        # Insert updated record on the new page.
        new_slot_id = new_page.insert_record(record)

        new_page_id = new_page.header.page_id

        self.save_page(new_page_id)

        try:

            # Delete old record after new record is saved.
            old_page.delete_record(slot_id)

            self.save_page(page_id)

        except Exception:

            # Best-effort cleanup if deleting the old
            # record fails.
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
        print(
            manager.read_record(
                location1[0],
                location1[1]
            )
        )

        # UPDATE
        updated_location = manager.update_record(
            location2[0],
            location2[1],
            Record([102, "Ravi", 25])
        )

        print("\nAfter Update:")
        print(
            manager.read_record(
                updated_location[0],
                updated_location[1]
            )
        )

        # DELETE
        manager.delete_record(
            location3[0],
            location3[1]
        )

        print("\nAfter Delete:")

        try:
            manager.read_record(
                location3[0],
                location3[1]
            )

        except ValueError as error:
            print(error)

        # RELOAD DATABASE
        print("\n=== Persistence Test ===")

        manager2 = PageManager(database_file)

        print("Recovered Page IDs:")
        print(manager2.get_all_page_ids())

        print("Recovered Record:")
        print(
            manager2.read_record(
                location1[0],
                location1[1]
            )
        )

        print("\n=== Page Manager Test Complete ===")
