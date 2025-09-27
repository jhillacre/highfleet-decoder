import os

from src.support import AppendOnlyFileBackedSet, JSONBackedDict


def test_append_only_file_backed_set():
    try:
        # Create a temporary file for testing
        filename = "AppendOnlyFileBackedSet.txt"

        # Initialize the AppendOnlyFileBackedSet
        set_obj = AppendOnlyFileBackedSet(filename, "Test Set", "item")

        # Add items to the set
        set_obj.add("item1")
        set_obj.add("item2")
        set_obj.add("item3")

        # Check if the items are in the set
        assert "item1" in set_obj
        assert "item2" in set_obj
        assert "item3" in set_obj

        # Remove an item from the set
        try:
            set_obj.remove("item2")
        except NotImplementedError:
            pass

        # Check if the item is removed from the set
        assert "item2" in set_obj

        # Save the set to the file
        set_obj.save()

        # Create a new AppendOnlyFileBackedSet from the saved file
        new_set_obj = AppendOnlyFileBackedSet(filename, "Test Set", "item")

        # Load the set from the file
        new_set_obj.load()

        # Check if the items are loaded correctly
        assert "item1" in new_set_obj
        assert "item2" in new_set_obj
        assert "item3" in new_set_obj

        assert os.path.exists(filename)
        contents = open(filename).read()
        assert "item1" in contents
        assert "item2" in contents
        assert "item3" in contents
    finally:
        # Clean up the temporary file
        if os.path.exists(filename):
            os.remove(filename)


def test_json_backed_dict():
    try:
        # Create a temporary file for testing
        filename = "JSONBackedDict.json"

        # Initialize the JSONBackedDict
        dict_obj = JSONBackedDict(filename, "Test Dict", "item")

        # Add items to the dict
        dict_obj["item1"] = "value1"
        dict_obj["item2"] = "value2"
        dict_obj["item3"] = "value3"

        # Check if the items are in the dict
        assert dict_obj["item1"] == "value1"
        assert dict_obj["item2"] == "value2"
        assert dict_obj["item3"] == "value3"

        # Remove an item from the dict
        del dict_obj["item2"]

        # Check if the item is removed from the dict
        assert "item2" not in dict_obj

        # overwrite an item in the dict
        dict_obj["item3"] = "new_value3"

        # Save the dict to the file
        dict_obj.save()

        # Create a new JSONBackedDict from the saved file
        new_dict_obj = JSONBackedDict(filename, "Test Dict", "item")

        # Load the dict from the file
        new_dict_obj.load()

        # Check if the items are loaded correctly
        assert new_dict_obj["item1"] == "value1"
        assert new_dict_obj["item3"] == "new_value3"

        assert os.path.exists(filename)
        contents = open(filename).read()
        assert "item1" in contents
        assert "item2" not in contents
        assert "item3" in contents
    finally:
        # Clean up the temporary file
        if os.path.exists(filename):
            os.remove(filename)
