
from pathlib import Path
import tempfile

from storage.page_manager import PageManager
from storage.page_engine import Record


print("=== MyRDB Multi-Page CRUD Test ===")

with tempfile.TemporaryDirectory() as temp_dir:

    database_file = Path(temp_dir) / "crud_test.db"

    manager = PageManager(database_file)

    # =========================
    # INSERT
    # =========================

    location1 = manager.insert_record(
        Record(["A" * 4000])
    )

    location2 = manager.insert_record(
        Record(["B" * 100])
    )

    print("\nInitial Locations:")
    print("Record 1:", location1)
    print("Record 2:", location2)

    print("\nInitial Page IDs:")
    print(manager.get_all_page_ids())

    # =========================
    # UPDATE WITH RELOCATION
    # =========================

    updated_location = manager.update_record(
        location2[0],
        location2[1],
        Record(["C" * 4000])
    )

    print("\nUpdated Record Location:")
    print(updated_location)

    print("\nPage IDs After Update:")
    print(manager.get_all_page_ids())

    updated_record = manager.read_record(
        updated_location[0],
        updated_location[1]
    )

    print("\nUpdated Record Length:")
    print(len(updated_record.values[0]))

    print("Updated Record Prefix:")
    print(updated_record.values[0][:10])

    # Verify old location is deleted
    print("\nChecking Old Location:")

    try:

        manager.read_record(
            location2[0],
            location2[1]
        )

    except ValueError as error:

        print(error)

    # =========================
    # DELETE FROM ANOTHER PAGE
    # =========================

    manager.delete_record(
        location1[0],
        location1[1]
    )

    print("\nDeleted Record 1:")

    try:

        manager.read_record(
            location1[0],
            location1[1]
        )

    except ValueError as error:

        print(error)

    # =========================
    # PERSISTENCE TEST
    # =========================

    print("\n=== Persistence Test ===")

    manager2 = PageManager(database_file)

    print("\nRecovered Page IDs:")
    print(manager2.get_all_page_ids())

    recovered_record = manager2.read_record(
        updated_location[0],
        updated_location[1]
    )

    print("\nRecovered Updated Record:")
    print(len(recovered_record.values[0]))
    print(recovered_record.values[0][:10])

    print("\n=== Multi-Page CRUD Test Complete ===")
