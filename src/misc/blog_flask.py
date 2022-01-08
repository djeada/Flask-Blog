import json
from flask import Flask
from pathlib import Path


class BlogFlask(Flask):
    """
    Custom Flask class, implementing specific Flask configuration for the blog.
    """
    def __init__(self, path_to_config: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        credentials = BlogFlask.parse_credentials(path_to_config)

        self.config['MYSQL_HOST'] = credentials['host']
        self.config['MYSQL_USER'] = credentials['user']
        self.config['MYSQL_PASSWORD'] = credentials['password']
        self.config['MYSQL_DB'] = credentials['database']
        self.config['MYSQL_CURSORCLASS'] = credentials['cursor_class']
        self.secret_key = 'secret123'

    @staticmethod
    def parse_credentials(path_to_config: Path) -> dict:
        """
        Parse the credentials from the JSON file.
        :param path_to_config: Path to the JSON file containing the credentials. 
        :return: dict.
        """
        with open(path_to_config) as file_object:
            credentials = json.load(file_object)

        # check if all credentials are present in the config file
        # throw exception if not
        for key in ['host', 'user', 'password', 'database', 'cursor_class']:
            if key not in credentials:
                raise Exception('Missing credentials for {}'.format(key))

        return credentials

