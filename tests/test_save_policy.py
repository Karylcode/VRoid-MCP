import pathlib
import pytest
from vroid_mcp.runtime import save_destination


@pytest.mark.parametrize('name', ['../old.vroid','C:\\old.vroid','a/b.vroid','a:stream.vroid',
                                'CON.vroid','LPT1.vroid','.vroid','old.vroid ','old.png',
                                'a?.vroid','a*.vroid','a|b.vroid','a\n.vroid'])
def test_reject_unsafe_or_non_model_names(tmp_path, name):
    with pytest.raises((ValueError,FileExistsError)):
        save_destination(tmp_path,name)


def test_existing_contents_are_preserved(tmp_path):
    folder=tmp_path/'saves';folder.mkdir()
    original=folder/'character.vroid';original.write_bytes(b'keep this character')
    with pytest.raises(FileExistsError):save_destination(tmp_path,'character.vroid')
    assert original.read_bytes()==b'keep this character'


def test_new_file_is_confined_to_saves(tmp_path):
    assert save_destination(tmp_path,'測試角色.vroid')==tmp_path/'saves'/'測試角色.vroid'
