
from pathlib import Path
import tempfile

from storage.page_manager import PageManager
from storage.page_engine import Record


print("=== MyRDB Storage Stress Test ===")

TOTAL_RECORDS = 500
NORMAL_RECORD_SIZE = 700
UPDATED_RECORD_SIZE = 1500
REUSE_RECORD_SIZE = 3000

with tempfile.TemporaryDirectory() as temp_dir:

    database_file = Path(temp_dir) / "stress_test.db"
    manager = PageManager(database_file)

    expected_records = {}
    locations = {}

    # =====================================
    # TEST 1: Insert 500 Records
    # =====================================

    print("\n[TEST 1] Large-Scale Record Insertion")

    for record_id in range(TOTAL_RECORDS):

        key = str(record_id)

        payload_size = (
            NORMAL_RECORD_SIZE - len(key) - 1
        )

        record = Record([
            key,
            "x" * payload_size
        ])

        location = manager.insert_record(record)

        locations[record_id] = location
        expected_records[record_id] = record.values

    assert manager.get_page_count() > 1
    assert len(locations) == TOTAL_RECORDS
    assert manager.validate_free_space_map()
    assert manager.validate_reusable_pages()

    print("Records inserted:", len(locations))
    print("Total pages:", manager.get_page_count())
    print("PASS")

    # =====================================
    # TEST 2: Verify All Inserted Records
    # =====================================

    print("\n[TEST 2] Record Read Verification")

    for record_id in range(TOTAL_RECORDS):

        record = manager.read_record(
            *locations[record_id]
        )

        assert record.values == expected_records[record_id]

    print("All 500 records verified.")
    print("PASS")

    # =====================================
    # TEST 3: Update Records With Relocation
    # =====================================

    print("\n[TEST 3] Large Record Updates")

    relocation_count = 0

    for record_id in range(0, TOTAL_RECORDS, 25):

        key = str(record_id)

        payload_size = (
            UPDATED_RECORD_SIZE - len(key) - 1
        )

        updated_record = Record([
            key,
            "u" * payload_size
        ])

        old_location = locations[record_id]

        new_location = manager.update_record(
            *old_location,
            updated_record
        )

        locations[record_id] = new_location
        expected_records[record_id] = updated_record.values

        if new_location != old_location:
            relocation_count += 1

        assert manager.read_record(
            *new_location
        ).values == updated_record.values

    assert relocation_count > 0

    print("Updates performed:", 20)
    print("Records relocated:", relocation_count)
    print("PASS")

    # =====================================
    # TEST 4: Empty First Page
    # =====================================

    print("\n[TEST 4] Empty Page Detection")

    deleted_ids = set()

    for record_id in range(TOTAL_RECORDS):

        if locations[record_id][0] == 0:

            manager.delete_record(
                *locations[record_id]
            )

            deleted_ids.add(record_id)

    assert manager.get_page(0).header.record_count == 0
    assert 0 in manager.get_reusable_pages()

    print("Deleted records from Page 0:", len(deleted_ids))
    print("Reusable pages:", manager.get_reusable_pages())
    print("PASS")

    # =====================================
    # TEST 5: Reuse Empty Page
    # =====================================

    print("\n[TEST 5] Empty Page Reuse")

    reuse_key = "STRESS_REUSE"

    reuse_record = Record([
        reuse_key,
        "r" * (REUSE_RECORD_SIZE - len(reuse_key) - 1)
    ])

    reuse_location = manager.insert_record(reuse_record)

    assert reuse_location == (0, 0)
    assert manager.read_record(
        *reuse_location
    ).values == reuse_record.values

    assert manager.get_page_count() == len(manager.get_all_page_ids())

    print("Reused page location:", reuse_location)
    print("PASS")

    manager.delete_record(*reuse_location)

    assert 0 in manager.get_reusable_pages()

    # =====================================
    # TEST 6: Additional Deletions
    # =====================================

    print("\n[TEST 6] Repeated Deletions")

    for record_id in range(0, TOTAL_RECORDS, 7):

        if record_id in deleted_ids:
            continue

        manager.delete_record(
            *locations[record_id]
        )

        deleted_ids.add(record_id)

    for record_id in deleted_ids:
        expected_records.pop(record_id, None)

    print("Total deleted original records:", len(deleted_ids))
    print("PASS")

    # =====================================
    # TEST 7: Compact All Pages
    # =====================================

    print("\n[TEST 7] Database Page Compaction")

    reclaimed_space = manager.compact_all_pages()

    assert manager.validate_free_space_map()
    assert manager.validate_reusable_pages()

    for page_id in manager.get_all_page_ids():
        assert manager.get_page(page_id).validate()

    print("Total additional contiguous space reclaimed:", reclaimed_space)
    print("All pages validated.")
    print("PASS")

    # =====================================
    # TEST 8: Persistence After Reload
    # =====================================

    print("\n[TEST 8] Database Reload")

    manager.save_all_pages()

    recovered_manager = PageManager(database_file)

    assert (
        recovered_manager.get_all_page_ids()
        == manager.get_all_page_ids()
    )

    for record_id, expected_values in expected_records.items():

        location = locations[record_id]

        recovered_record = recovered_manager.read_record(
            *location
        )

        assert recovered_record.values == expected_values

    print("Recovered records:", len(expected_records))
    print("Recovered pages:", recovered_manager.get_page_count())
    print("PASS")

    # =====================================
    # TEST 9: Deleted Record Verification
    # =====================================

    print("\n[TEST 9] Deleted Record Verification")

    for record_id in deleted_ids:

        try:
            recovered_manager.read_record(
                *locations[record_id]
            )

        except ValueError:
            continue

        raise AssertionError(
            f"Deleted record {record_id} is still readable"
        )

    print("All deleted records correctly rejected.")
    print("PASS")

    # =====================================
    # TEST 10: Reuse After Reload
    # =====================================

    print("\n[TEST 10] Page Reuse After Reload")

    assert 0 in recovered_manager.get_reusable_pages()

    final_key = "FINAL_STRESS"

    final_record = Record([
        final_key,
        "f" * (REUSE_RECORD_SIZE - len(final_key) - 1)
    ])

    final_location = recovered_manager.insert_record(
        final_record
    )

    assert final_location == (0, 0)

    assert recovered_manager.read_record(
        *final_location
    ).values == final_record.values

    print("Final reused location:", final_location)
    print("PASS")

    # =====================================
    # TEST 11: Final Metadata Validation
    # =====================================

    print("\n[TEST 11] Final Storage Validation")

    assert recovered_manager.validate_free_space_map()
    assert recovered_manager.validate_reusable_pages()

    for page_id in recovered_manager.get_all_page_ids():
        assert recovered_manager.get_page(page_id).validate()

    print("Free space map: Valid")
    print("Reusable page tracking: Valid")
    print("All page headers and structures: Valid")
    print("PASS")


print("\n================================")
print("ALL STORAGE STRESS TESTS PASSED")
print("================================")
