from pathlib import Path
import enum
import typing

from hat import json


package_path: Path = Path(__file__).parent

json_schema_repo: json.SchemaRepository = json.SchemaRepository(
    json.json_schema_repo,
    json.SchemaRepository.from_json(package_path / 'json_schema_repo.json'))


class Order(enum.Enum):
    ASC = 'ASC'
    DESC = 'DESC'


class Status(enum.Enum):
    PENDING = 0
    RUNNING = 1
    SUCCESS = 2
    FAILURE = 3


class Commit(typing.NamedTuple):
    repo: str
    hash: str
    change: int
    status: Status
    output: str
