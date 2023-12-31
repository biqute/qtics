"""Replace all occurence of words in REPLACE_MAP.

Exclude hidden files and directory, exclude special
files and folders defined in EXCLUDE.
"""
import os
import re

EXCLUDE = ["./docs/build", "__pycache__", "rename.py"]

REPLACE_MAP = [
    ("qinst", "qtics"),
    ("Qinst", "Qtics"),
    ("QINST", "QTICS"),
]


def replace_text_in_files(folder_path):
    """Replace all occurence of words in REPLACE_MAP."""
    for foldername, subfolders, filenames in os.walk(folder_path):
        # Exclude folders and files that start with a dot
        subfolders[:] = [
            subfolder for subfolder in subfolders if not subfolder.startswith(".")
        ]
        filenames[:] = [
            filename for filename in filenames if not filename.startswith(".")
        ]

        for filename in filenames:
            try:
                file_path = os.path.join(foldername, filename)

                check_exclude = False
                for i in EXCLUDE:
                    if i in file_path:
                        check_exclude = True
                if check_exclude:
                    continue

                print(f"Checking {file_path}")

                # Process only files (not directories)
                if os.path.isfile(file_path):
                    with open(file_path, encoding="utf-8") as file:
                        file_content = file.read()

                    for start, finish in REPLACE_MAP:
                        file_content = re.sub(start, finish, file_content)

                    with open(file_path, "w", encoding="utf-8") as file:
                        file.write(file_content)

                new_filename = filename
                for start, finish in REPLACE_MAP:
                    new_filename = new_filename.replace(start, finish)
                new_file_path = os.path.join(foldername, new_filename)
                os.rename(file_path, new_file_path)
            except:
                pass

        for subfolder in subfolders:
            # Rename the subfolder
            new_subfolder = subfolder
            for start, finish in REPLACE_MAP:
                new_subfolder = new_subfolder.replace(start, finish)
            new_subfolder_path = os.path.join(foldername, new_subfolder)
            os.rename(os.path.join(foldername, subfolder), new_subfolder_path)


if __name__ == "__main__":
    folder_path = "."
    replace_text_in_files(folder_path)
    print("\nText replacement completed.")
