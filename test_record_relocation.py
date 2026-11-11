
from pathlib import Path
import tempfile

from storage.page_manager import PageManager
from storage.page_engine import Record


print("=== MyRDB Actual Relocation Test ===")

with tempfile.TemporaryDirectory() as temp_dir:

    database_file = Path(temp_dir) / "relocation.db"

    manager = PageManager(database_file)

    # Fill Page 0
    location_a = manager.insert_record(
        Record(["A" * 4000])
    )

    # Fill Page 1 partially
    location_b = manager.insert_record(
        Record(["B" * 3000])
    )

    location_c = manager.insert_record(
        Record(["C" * 900])
    )

    print("\nInitial Locations:")
    print("A:", location_a)
    print("B:", location_b)
    print("C:", location_c)

    print("\nInitial Page IDs:")
    print(manager.get_all_page_ids())

    # Update B from 3000 bytes to 4000 bytes.
    # Page 1 cannot accommodate the larger record.
    updated_location = manager.update_record(
        location_b[0],
        location_b[1],
        Record(["D" * 4000])
    )

    print("\nUpdated Location:")
    print(updated_location)

    print("\nPage IDs After Update:")
    print(manager.get_all_page_ids())

    print("\nTotal Pages:")
    print(manager.get_page_count())

    # Verify updated record
    updated = manager.read_record(
        updated_location[0],
        updated_location[1]
    )

    print("\nUpdated Record:")
    print("Length:", len(updated.values[0]))
    print("Prefix:", updated.values[0][:10])

    # Verify old location is deleted
    print("\nOld Location Check:")

    try:
        manager.read_record(
            location_b[0],
            location_b[1]
        )

    except ValueError as error:
        print(error)

    # Persistence test
    print("\n=== Persistence Test ===")

    manager2 = PageManager(database_file)

    recovered = manager2.read_record(
        updated_location[0],
        updated_location[1]
    )

    print("Recovered Record Length:")
    print(len(recovered.values[0]))

    print("Recovered Page IDs:")
    print(manager2.get_all_page_ids())

print("\n=== Actual Relocation Test Complete ===")
