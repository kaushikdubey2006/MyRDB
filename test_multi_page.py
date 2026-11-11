
from pathlib import Path
import tempfile

from storage.page_manager import PageManager
from storage.page_engine import Record


print("=== MyRDB Multi-Page Allocation Test ===")

with tempfile.TemporaryDirectory() as temp_dir:

    database_file = Path(temp_dir) / "multi_page.db"

    manager = PageManager(database_file)

    # =========================
    # INSERT FIRST LARGE RECORD
    # =========================

    record1 = Record(["A" * 4000])

    location1 = manager.insert_record(record1)

    print("\nFirst Record Location:")
    print(location1)

    print("Total Pages:")
    print(manager.get_page_count())

    # =========================
    # INSERT SECOND LARGE RECORD
    # =========================

    record2 = Record(["B" * 100])

    location2 = manager.insert_record(record2)

    print("\nSecond Record Location:")
    print(location2)

    print("Total Pages:")
    print(manager.get_page_count())

    # =========================
    # VERIFY PAGE ALLOCATION
    # =========================

    print("\nAllocated Page IDs:")
    print(manager.get_all_page_ids())

    # =========================
    # READ RECORDS
    # =========================

    print("\nVerify First Record:")

    result1 = manager.read_record(
        location1[0],
        location1[1]
    )

    print(len(result1.values[0]))
    print(result1.values[0][:10])

    print("\nVerify Second Record:")

    result2 = manager.read_record(
        location2[0],
        location2[1]
    )

    print(len(result2.values[0]))
    print(result2.values[0][:10])

    # =========================
    # PERSISTENCE TEST
    # =========================

    print("\n=== Multi-Page Persistence Test ===")

    manager2 = PageManager(database_file)

    print("\nRecovered Page IDs:")
    print(manager2.get_all_page_ids())

    print("\nRecovered First Record:")

    recovered1 = manager2.read_record(
        location1[0],
        location1[1]
    )

    print(len(recovered1.values[0]))

    print("\nRecovered Second Record:")

    recovered2 = manager2.read_record(
        location2[0],
        location2[1]
    )

    print(len(recovered2.values[0]))

    print("\n=== Multi-Page Test Complete ===")
