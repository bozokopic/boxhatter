from pathlib import Path

from hat import json


package_path: Path = Path(__file__).parent

json_schema_repo: json.SchemaRepository = json.SchemaRepository(
    json.json_schema_repo,
    json.SchemaRepository.from_json(package_path / 'json_schema_repo.json'))
