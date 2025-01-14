import json
import os

class JsonFile:
    def __init__(self, file_path):
        self.file_path = file_path
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding='ascii') as f:
                json.dump({"voters": {}}, f)
        self.__data = self.__read_json()

    @property
    def data(self):
        return self.__data

    def save(self):
        self.__write_json(self.data)

    def __read_json(self):
        with open(self.file_path, "r") as f:
            return json.load(f)

    def __write_json(self, data):
        with open(self.file_path, 'w', encoding='ascii') as f:
            json.dump(data, f, indent=4)