import pytest
from vroid_mcp.runtime import review_folder, validate_capture


@pytest.mark.parametrize('capture_id',['../x','a/b','C:\\escape','', 'z'*32])
def test_review_lookup_stays_in_lab(tmp_path,capture_id):
    with pytest.raises(ValueError):review_folder(tmp_path,capture_id)


@pytest.mark.parametrize('views,size',[([],1024),(['front','front'],1024),(['../x'],1024),(['front'],255),(['front'],2049),(['front'],512.5)])
def test_invalid_capture_requests(views,size):
    with pytest.raises(ValueError):validate_capture(views,size)
