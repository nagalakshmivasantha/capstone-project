from pathlib import Path

from app.storage.minio_adapter import MinioAdapter


def test_local_storage_fallback_upload_and_download(tmp_path: Path) -> None:
    source = tmp_path / "features.csv"
    source.write_text("entity_id,feature_value\nA,1\n", encoding="utf-8")
    adapter = MinioAdapter(base_dir=str(tmp_path / "object-store"), mode="local")

    upload = adapter.upload_file("features", str(source), "daily/features.csv")
    assert upload["backend"] == "local"
    assert upload["status"] == "uploaded"
    assert adapter.list_objects("features")["objects"][0]["object_name"] == "daily/features.csv"

    destination = tmp_path / "downloaded.csv"
    result = adapter.download_file("features", "daily/features.csv", str(destination))
    assert result["status"] == "downloaded"
    assert destination.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
