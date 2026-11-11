
from pathlib import Path
import tempfile

from storage.page_manager import PageManager
from storage.page_engine import Record


print("=== MyRDB Record Compaction Test ===")

with tempfile.TemporaryDirectory() as temp_dir:

    database_file = Path(temp_dir) / "compaction.db"

    manager = PageManager(database_file)

    # TEST 1: Insert three records.
    print("\n[TEST 1] Insert Records")

    location_a = manager.insert_record(
        Record(["A" * 1000])
    )

    location_b = manager.insert_record(
        Record(["B" * 1000])
    )

    location_c = manager.insert_record(
        Record(["C" * 1000])
    )

    print("Locations:", location_a, location_b, location_c)
    print("PASS")

    # TEST 2: Create Fragmentation.
    print("\n[TEST 2] Create Fragmentation")

    manager.delete_record(*location_a)

    page = manager.get_page(0)

    free_before = page.calculate_free_space()

    print("Free space before compaction:", free_before)

    # Insertion should fail because contiguous space is insufficient.
    try:
        page.insert_record(Record(["D" * 1500]))
        raise AssertionError("Expected insertion to fail")

    except ValueError as error:
        print("Insertion failed before compaction:", error)

    print("PASS")

    # TEST 3: Compact Page.
    print("\n[TEST 3] Compact Page")

    reclaimed = manager.compact_page(0)

    free_after = page.calculate_free_space()

    print("Additional free space:", reclaimed)
    print("Free space after compaction:", free_after)

    assert free_after > free_before
    assert page.validate()

    print("PASS")

    # TEST 4: Insert into reclaimed space.
    print("\n[TEST 4] Insert After Compaction")

    location_d = manager.insert_record(
        Record(["D" * 1500])
    )

    print("New record location:", location_d)

    record_d = manager.read_record(*location_d)

    assert record_d.values == ["D" * 1500]

    print("PASS")

    # TEST 5: Verify Existing Records.
    print("\n[TEST 5] Verify Existing Records")

    # A was deleted and its slot was reused by D.
    # B and C must remain readable.

    assert location_a == location_d

    assert manager.read_record(*location_b).values == ["B" * 1000]

    assert manager.read_record(*location_c).values == ["C" * 1000]

    assert manager.read_record(*location_d).values == ["D" * 1500]

    print("Record B remains readable.")
    print("Record C remains readable.")
    print("Deleted slot A successfully reused by D.")
    print("PASS")

    # TEST 6: Persistence After Reload.
    print("\n[TEST 6] Persistence")

    manager.save_all_pages()

    manager2 = PageManager(database_file)

    assert manager2.read_record(*location_b).values == ["B" * 1000]

    assert manager2.read_record(*location_c).values == ["C" * 1000]

    assert manager2.read_record(*location_d).values == ["D" * 1500]

    # Old location A now points to the reused slot containing D.
    assert manager2.read_record(*location_a).values == ["D" * 1500]

    assert manager2.get_page(0).validate()

    print("All active records recovered successfully.")
    print("Slot reuse survived database reload.")
    print("PASS")


print("\n================================")
print("ALL COMPACTION TESTS PASSED")
print("================================")
