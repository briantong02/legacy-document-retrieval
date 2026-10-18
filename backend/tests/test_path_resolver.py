from app.utils.path_utils import resolve_path


def test_resolve_path_matches_expected_example() -> None:
    canonical = r"e:\DATA1\IT\IDMFiles\infor\infor"
    local = "/mnt/idm/infor"
    source = r"E:\DATA1\IT\IDMFiles\infor\infor\H14824\0000540b-cfc3-4f49-96f4-9f14d772f9a4"

    resolved = resolve_path(source, canonical, local)

    assert resolved == "/mnt/idm/infor/H14824/0000540b-cfc3-4f49-96f4-9f14d772f9a4"


def test_resolve_path_is_case_insensitive_for_root() -> None:
    canonical = r"e:\data1\it\idmfiles\infor\infor"
    local = "/mnt/idm/infor"
    source = r"E:\DATA1\IT\IDMFiles\infor\infor\Folder\Doc"

    resolved = resolve_path(source, canonical, local)

    assert resolved == "/mnt/idm/infor/Folder/Doc"


def test_resolve_path_tolerates_doubled_backslash_root() -> None:
    # Regression: an over-escaped canonical root (doubled backslashes) must still
    # resolve against a real single-backslash DocumentPath. This was the cause of
    # the invalid_document_path error in the field.
    canonical = r"e:\\DATA1\\IT\\IDMFiles\\infor\\infor"
    local = "/mnt/idm/infor"
    source = r"E:\DATA1\IT\IDMFiles\infor\infor\H14824\0000540b-cfc3-4f49-96f4-9f14d772f9a4"

    resolved = resolve_path(source, canonical, local)

    assert resolved == "/mnt/idm/infor/H14824/0000540b-cfc3-4f49-96f4-9f14d772f9a4"
