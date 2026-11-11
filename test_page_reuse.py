
from pathlib import Path
import tempfile

from storage.page_manager import PageManager
from storage.page_engine import Record


print("=== MyRDB Page Reuse Test ===")

with tempfile.TemporaryDirectory() as temp_dir:

    database_file = Path(temp_dir) / "page_reuse.db"

    manager = PageManager(database_file)

    # TEST 1: Insert records into one page.
    print("\n[TEST 1] Fill First Page")

    locations = []

    for name in ["A", "B", "C"]:

        location = manager.insert_record(
            Record([name * 1000])
        )

        locations.append(location)

    assert manager.get_page_count() == 1

    assert manager.validate_free_space_map()
    assert manager.validate_reusable_pages()

    print("Page IDs:", manager.get_all_page_ids())
    print("PASS")

    # TEST 2: Delete all records.
    print("\n[TEST 2] Delete All Records")

    for location in locations:
        manager.delete_record(*location)

    assert manager.get_page(0).header.record_count == 0

    assert manager.get_reusable_pages() == [0]

    print("Reusable Pages:", manager.get_reusable_pages())
    print("PASS")

    # TEST 3: Reuse empty page.
    print("\n[TEST 3] Reuse Empty Page")

    new_location = manager.insert_record(
        Record(["D" * 3500])
    )

    print("New Location:", new_location)

    assert new_location == (0, 0)

    assert manager.get_page_count() == 1

    assert manager.read_record(*new_location).values == ["D" * 3500]

    assert manager.get_reusable_pages() == []

    print("Existing empty page successfully reused.")
    print("PASS")

    # TEST 4: Delete and prepare persistence test.
    print("\n[TEST 4] Prepare Persistence Test")

    manager.delete_record(*new_location)

    manager.save_all_pages()

    assert manager.get_reusable_pages() == [0]

    print("PASS")

    # TEST 5: Recover reusable page after reload.
    print("\n[TEST 5] Reusable Page Recovery")

    manager2 = PageManager(database_file)

    print("Recovered Pages:", manager2.get_all_page_ids())

    print("Recovered Reusable Pages:", manager2.get_reusable_pages())

    assert manager2.get_reusable_pages() == [0]

    assert manager2.validate_free_space_map()
    assert manager2.validate_reusable_pages()

    print("PASS")

    # TEST 6: Reuse recovered page.
    print("\n[TEST 6] Reuse After Reload")

    final_location = manager2.insert_record(
        Record(["E" * 3500])
    )

    assert final_location == (0, 0)

    assert manager2.read_record(*final_location).values == ["E" * 3500]

    assert manager2.get_page_count() == 1

    assert manager2.get_reusable_pages() == []

    print("Final Location:", final_location)
    print("PASS")

    # TEST 7: Validate free-space tracking.
    print("\n[TEST 7] Validate Free Space Map")

    assert manager2.validate_free_space_map()

    assert manager2.validate_reusable_pages()

    print("Free Space Map:", manager2.get_free_space_map())
    print("PASS")


print("\n================================")
print("ALL PAGE REUSE TESTS PASSED")
print("================================")
