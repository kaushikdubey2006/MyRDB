
from pathlib import Path
import tempfile

from storage.page_manager import PageManager
from storage.page_engine import Record


def run_test():

    print("=== MyRDB Chapter 4 Integration Test ===")

    with tempfile.TemporaryDirectory() as temp_dir:

        database_file = Path(temp_dir) / "integration.db"

        manager = PageManager(database_file)

        # =================================
        # TEST 1: MULTI-PAGE INSERT
        # =================================

        print("\n[TEST 1] Multi-Page Insert")

        location_a = manager.insert_record(
            Record(["A" * 4000])
        )

        location_b = manager.insert_record(
            Record(["B" * 3000])
        )

        location_c = manager.insert_record(
            Record(["C" * 900])
        )

        assert location_a == (0, 0)
        assert location_b == (1, 0)
        assert location_c == (1, 1)

        print("Locations:", location_a, location_b, location_c)
        print("Page IDs:", manager.get_all_page_ids())
        print("PASS")

        # =================================
        # TEST 2: MULTI-PAGE READ
        # =================================

        print("\n[TEST 2] Multi-Page Read")

        record_a = manager.read_record(*location_a)
        record_b = manager.read_record(*location_b)
        record_c = manager.read_record(*location_c)

        assert len(record_a.values[0]) == 4000
        assert len(record_b.values[0]) == 3000
        assert len(record_c.values[0]) == 900

        print("All three records read successfully.")
        print("PASS")

        # =================================
        # TEST 3: UPDATE ON SAME PAGE
        # =================================

        print("\n[TEST 3] Update On Same Page")

        updated_b = manager.update_record(
            location_b[0],
            location_b[1],
            Record(["D" * 2500])
        )

        assert updated_b == location_b

        result_b = manager.read_record(*updated_b)

        assert len(result_b.values[0]) == 2500
        assert result_b.values[0][0] == "D"

        print("Updated location:", updated_b)
        print("PASS")

        # =================================
        # TEST 4: UPDATE WITH RELOCATION
        # =================================

        print("\n[TEST 4] Update With Relocation")

        relocated_b = manager.update_record(
            updated_b[0],
            updated_b[1],
            Record(["E" * 4000])
        )

        assert relocated_b != updated_b
        assert relocated_b[0] == 2

        relocated_record = manager.read_record(*relocated_b)

        assert len(relocated_record.values[0]) == 4000
        assert relocated_record.values[0][0] == "E"

        print("Old location:", updated_b)
        print("New location:", relocated_b)
        print("PASS")

        # =================================
        # TEST 5: OLD LOCATION DELETED
        # =================================

        print("\n[TEST 5] Old Location Check")

        try:

            manager.read_record(*updated_b)

            raise AssertionError(
                "Old record location should be deleted"
            )

        except ValueError as error:

            assert str(error) == "Record has been deleted"

        print("Old location correctly marked deleted.")
        print("PASS")

        # =================================
        # TEST 6: MULTI-PAGE DELETE
        # =================================

        print("\n[TEST 6] Multi-Page Delete")

        manager.delete_record(
            location_a[0],
            location_a[1]
        )

        try:

            manager.read_record(*location_a)

            raise AssertionError(
                "Deleted record should not be readable"
            )

        except ValueError as error:

            assert str(error) == "Record has been deleted"

        print("Record deleted successfully from Page 0.")
        print("PASS")

        # =================================
        # TEST 7: DATABASE PERSISTENCE
        # =================================

        print("\n[TEST 7] Persistence After Reload")

        manager.save_all_pages()

        manager2 = PageManager(database_file)

        assert manager2.get_all_page_ids() == [0, 1, 2]

        recovered = manager2.read_record(*relocated_b)

        assert len(recovered.values[0]) == 4000
        assert recovered.values[0][0] == "E"

        recovered_c = manager2.read_record(*location_c)

        assert len(recovered_c.values[0]) == 900

        print("Recovered Page IDs:", manager2.get_all_page_ids())
        print("Relocated record recovered successfully.")
        print("PASS")

        # =================================
        # TEST 8: PAGE VALIDATION
        # =================================

        print("\n[TEST 8] Page Validation")

        for page_id in manager2.get_all_page_ids():

            page = manager2.get_page(page_id)

            assert page.validate() is True

            print(f"Page {page_id}: Valid")

        print("PASS")

        # =================================
        # FINAL RESULT
        # =================================

        print("\n=================================")
        print("ALL CHAPTER 4 TESTS PASSED")
        print("Total Pages:", manager2.get_page_count())
        print("Page IDs:", manager2.get_all_page_ids())
        print("=================================")


if __name__ == "__main__":
    run_test()
