from fastapi import HTTPException

from app.services.file_server import build_document_response


def test_build_document_response_turns_invalid_root_into_http_exception(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.file_server.resolve_path",
        lambda **_: (_ for _ in ()).throw(ValueError("bad root")),
    )
    monkeypatch.setattr(
        "app.services.file_server.get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "doc_root_canonical": r"e:\\DATA1\\IT\\IDMFiles\\infor\\infor",
                "doc_root_local": "/mnt/idm/infor",
            },
        )(),
    )

    try:
        build_document_response(
            document_path=r"e:\\DATA1\\IT\\IDMFiles\\infor\\infor\\x\\y",
            resource_name="file.pdf",
            as_download=True,
        )
    except HTTPException as exc:
        assert exc.status_code == 500
        assert exc.detail["code"] == "invalid_document_path"
        assert exc.detail["message"] == "Document path cannot be resolved"
    else:
        raise AssertionError("Expected HTTPException")
