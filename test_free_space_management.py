
from pathlib import Path
import tempfile

from storage.page_manager import PageManager
from storage.page_engine import Record


print("=== MyRDB Free Space Management Test ===")

with tempfile.TemporaryDirectory() as temp_dir:

    database_file = Path(temp_dir) / "free_space.db"

    manager = PageManager(database_file)

    # TEST 1: Insert records.
    print("\n[TEST 1] Free Space Tracking After Insert")

    location_a = manager.insert_record(
        Record(["A" * 1000])
    )

    location_b = manager.insert_record(
        Record(["B" * 1000])
    )

    location_c = manager.insert_record(
        Record(["C" * 1000])
    )

    for page_id in manager.get_all_page_ids():

        expected = manager.get_page(page_id).calculate_free_space()

        actual = manager.get_page_free_space(page_id)

        assert actual == expected

        print(f"Page {page_id}: {actual} bytes")

    print("PASS")

    # TEST 2: Delete a record.
    print("\n[TEST 2] Tracking After Delete")

    manager.delete_record(*location_a)

    expected = manager.get_page(0).calculate_free_space()

    actual = manager.get_page_free_space(0)

    assert actual == expected

    print("Updated free space:", actual)
    print("PASS")

    # TEST 3: Update a record.
    print("\n[TEST 3] Tracking After Update")

    updated_location = manager.update_record(
        *location_b,
        Record(["B" * 1200])
    )

    page_id = updated_location[0]

    expected = manager.get_page(page_id).calculate_free_space()

    actual = manager.get_page_free_space(page_id)

    assert actual == expected

    print("Updated location:", updated_location)
    print("Free space:", actual)
    print("PASS")

    # TEST 4: Compaction tracking.
    print("\n[TEST 4] Tracking After Compaction")

    manager.compact_page(0)

    expected = manager.get_page(0).calculate_free_space()

    actual = manager.get_page_free_space(0)

    assert actual == expected

    print("Free space after compaction:", actual)
    print("PASS")

    # TEST 5: Page selection.
    print("\n[TEST 5] Page Selection")

    selected_page = manager.find_page_with_free_space(100)

    assert selected_page is not None

    assert (
        manager.get_page_free_space(
            selected_page.header.page_id
        ) >= 100
    )

    print("Selected Page:", selected_page.header.page_id)
    print("PASS")

    # TEST 6: Rebuild map.
    print("\n[TEST 6] Rebuild Free Space Map")

    rebuilt_map = manager.rebuild_free_space_map()

    for page_id, free_space in rebuilt_map.items():

        assert free_space == (
            manager.get_page(page_id).calculate_free_space()
        )

    print("Rebuilt Map:", rebuilt_map)
    print("PASS")

    # TEST 7: Persistence after reload.
    print("\n[TEST 7] Persistence After Reload")

    manager.save_all_pages()

    manager2 = PageManager(database_file)

    for page_id in manager2.get_all_page_ids():

        expected = manager2.get_page(page_id).calculate_free_space()

        actual = manager2.get_page_free_space(page_id)

        assert actual == expected

    print("Recovered Map:", manager2.free_space_map)
    print("PASS")


print("\n================================")
print("ALL FREE SPACE TESTS PASSED")
print("================================")
