from __future__ import annotations
from typing import List, Dict, Set

from . import Dataset
from ..metadata import Metadata
from ..file.local import LocalFile

import os
import os.path
import yaml
import re
import csv
import datetime
import platform
from functools import cached_property

class LocalDataset(Dataset):
    """

    Attributes:
        _path (str): Path of the dataset
        _manifest_path (str): Path of the dataset manifest
        _includes (set): File inclusion rules
        _excludes (set): File exclusion rules
        _md5s (dict): MD5 hash cache of the files

    Class Attributes:
        _regexps (dict): Regular expression cache of the file rules
    """

    _regexps: Dict = {}

    def __init__(self, path: str, manifest_file: str="manifest.yaml"):
        """Initializes LocalDataset object.

        Args:
            path (str): Path of the dataset
            manifest_file (str): Name of the dataset manifest file (optional)

        Raises:
            NotADirectoryError = Invalid dataset path
        """
        # Call parent method
        super().__init__()

        # Throw exception if invalid path
        if not os.path.isdir(path):
            raise NotADirectoryError

        # Set path
        self._path = path

        # Set manifest path
        self._manifest_path = os.path.join(path, manifest_file)

        # Set file rules
        self._includes = None
        self._excludes = None

        # Load cached MD5 hashes
        self._load_md5s()


    def _get_manifest(self) -> Dict:
        """Retrieves dataset manifest

        Returns:
            Dataset manifest dictionary
        """
        # TODO: Add exception handling
        manifest = None
        if os.path.isfile(self._manifest_path):
            with open(self._manifest_path, "r") as file:
                # REMARK: safe_load returns None if file is empty
                manifest = yaml.safe_load(file)
        if not manifest:
            manifest = {}
        files = manifest.get("files", {})
        return {
            "metadata": manifest.get("metadata", {}),
            "template": manifest.get("template", ""),
            "files": {
                "includes": files.get("includes", []),
                "excludes": files.get("excludes", []),
            },
        }


    @cached_property
    def manifest(self) -> Dict:
        return self._get_manifest()


    @cached_property
    def path(self) -> str:
        """Path of the dataset"""
        return self._path


    @cached_property
    def template(self) -> str:
        """Metadata template of the dataset"""
        return self.manifest["template"]


    @property
    def includes(self) -> Set:
        """Inclusion rules of the dataset files"""
        if self._includes is None:
            manifest = self._get_manifest()
            self._includes = manifest["files"]["includes"]

        return self._includes


    @property
    def excludes(self) -> Set:
        """Exclusion rules of the dataset files"""
        if self._excludes is None:
            manifest = self._get_manifest()
            self._excludes = manifest["files"]["excludes"]

        return self._excludes


    def _get_metadata(self) -> Metadata:
        """Retrieves metadata of the dataset.

        Returns:
            Metadata of the dataset
        """
        manifest = self._get_manifest()

        return Metadata(**manifest["metadata"])


    def _set_manifest(self, manifest: Dict) -> None:
        """Stores the dataset manifest.

        Args:
            manifest (Dict): Dataset manifest

        Returns:
            None
        """
        if "metadata" not in manifest:
            manifest["metadata"] = {}

        if "files" not in manifest:
            manifest["files"] = {
                "includes": [],
                "excludes": [],
            }

        with open(self._manifest_path, "w") as file:
            # TODO: Exception handling
            yaml.emitter.Emitter.process_tag = lambda self, *args, **kw: None
            yaml.dump(manifest, file, default_flow_style=False)


    def save_metadata(self) -> None:
        manifest = self._get_manifest()
        manifest["metadata"] = self.metadata.serialize()
        self._set_manifest(manifest)


    def _match_rule(self, name: str, rule: str) -> bool:
        """Tests if a file name matches the specified rule.

        The asterisk (*) and question mark (?) are used as wildcard characters.
        The asterisk matches any sequence of characters.
        The question mark matches any single character.
        Relative path and file name are handled separately to support path rules.
        Cached regular expressions are created for each rule internally.

        Examples rules:
        *            : All files
        *.pdf        : Files with the .pdf extension, e.g. file.pdf
        *.xls*       : Files with the extension starting with .xls, e.g.
                       file.xls, file.xlsx
        table_??.cvs : Files with the .csv extension that start with
                       table_ and end with two additional characters, e.g.
                       table_01.csv, table_a5.csv
        data/*.cvs   : Files with the .csv extension under the data
                       directory, e.g. data/table.csv, data/results.csv
        data/*/*.cvs : Files with the .csv extension under the sub-directories
                       of the data directory, e.g. data/set1/results.csv,
                       data/set2/results.csv

        Returns:
            True if file name matches the rule, False otherwise

        Raises:
            None

        """
        if not rule in self._regexps:
            regexps = []
            for part in os.path.split(rule):
                if part:
                    pattern = re.escape(part).replace("\*", ".*").replace("\?", ".")
                    regexp = re.compile(f"^{pattern}$", re.IGNORECASE)
                else:
                    regexp = None
                regexps.append(regexp)
            self._regexps[rule] = regexps
        for i, part in enumerate(os.path.split(name)):
            regexp = self._regexps[rule][i]
            if part:
                if not regexp or not regexp.match(part):
                    return False
            elif regexp:
                return False
        return True


    def _get_files(self) -> List[LocalFile]:
        files = []
        excludes = self.excludes
        includes = self.includes
        dirs = [self.path]
        while dirs:
            dir = dirs.pop(0)
            for file in os.listdir(dir):
                fullpath = os.path.join(dir, file)
                if os.path.isdir(fullpath):
                    dirs.append(fullpath)
                else:
                    path = os.path.relpath(fullpath, self.path)

                    if fullpath == self._manifest_path:
                        continue

                    if includes:
                        matched = False
                        for rule in includes:
                            if self._match_rule(path, rule):
                                matched = True
                                break
                        if not matched:
                            continue
                    else:
                        continue

                    if excludes:
                        matched = False
                        for rule in excludes:
                            if self._match_rule(path, rule):
                                matched = True
                                break
                        if matched:
                            continue

                    size = None
                    md5 = None
                    if path in self._md5s:
                        date, size, md5 = self._md5s[path]
                        if not date or date != os.path.getmtime(fullpath) or size != os.path.getsize(fullpath):
                            size = None
                            md5 = None
                    file = LocalFile(
                        fullpath,
                        basepath = self.path,
                        md5 = md5
                    )
                    files.append(file)
        return files


    def _load_md5s(self) -> None:
        """Loads MD5 hashes stored in the dataset directory"""
        self._md5s = {}
        path = os.path.join(self.path, ".fairly_md5")
        try:
            with open(path, "r") as file:
                reader = csv.reader(file)
                for name, date, size, md5 in reader:
                    self._md5s[name] = (date, size, md5)
        except FileNotFoundError:
            pass


    def save_files(self) -> None:
        manifest = self._get_manifest()
        manifest["files"] = {
            "includes": self.includes,
            "excludes": self.excludes,
        }
        self._set_manifest(manifest)


    def upload(self, repository, notify: Callable=None) -> RemoteDataset:
        import fairly
        from ..client import Client

        # Get client
        if isinstance(repository, str):
            client = fairly.client(repository)
        elif isinstance(repository, Client):
            client = repository
        else:
            raise ValueError("Invalid repository")

        # Create dataset
        dataset = client.create_dataset(self.metadata)

        try:
            # Upload files
            files = self.get_files(refresh=True)
            for path, file in files.items():
                client.upload_file(dataset, file, notify)

        except:
            client.delete_dataset(dataset.id)
            raise

        return dataset


    @property
    def size(self) -> int:
        """Total size of the dataset in bytes."""
        size = 0
        for file in self.files:
            size += file.size

        return size


    @cached_property
    def created(self) -> datetime.datetime:
        """Creation date and time of the dataset"""
        # REMARK: On Unix systems getctime() returns the time of most recent
        # metadata change, but not the creation.
        # https://stackoverflow.com/questions/237079/how-do-i-get-file-creation-and-modification-date-times
        # https://docs.python.org/3/library/os.html#os.stat_result
        if platform.system() == "Windows":
            timestamp = os.path.getctime(self._manifest_path)

        else:
            stat = os.stat(self._manifest_path)
            try:
                timestamp = stat.st_birthtime
            except AttributeError:
                timestamp = stat.st_mtime

        return datetime.datetime.fromtimestamp(timestamp)


    @property
    def modified(self) -> datetime.datetime:
        """Last modification date and time of the dataset"""
        timestamp = os.path.getmtime(self._manifest_path)

        return datetime.datetime.fromtimestamp(timestamp)