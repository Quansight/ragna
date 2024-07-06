from fastapi import status
from fastapi.testclient import TestClient

from ragna.deploy import Config
from ragna.deploy._api import app
from tests.deploy.utils import authenticate_with_api


def test_batch_sequential_upload_equivalence(tmp_local_root):
    "Check that uploading documents sequentially and in batch gives the same result"
    config = Config(local_root=tmp_local_root)

    document_root = config.local_root / "documents"
    document_root.mkdir()
    document_path1 = document_root / "test1.txt"
    with open(document_path1, "w") as file:
        file.write("!\n")
    document_path2 = document_root / "test2.txt"
    with open(document_path2, "w") as file:
        file.write("?\n")

    with TestClient(
        app(config=Config(), ignore_unavailable_components=False)
    ) as client:
        authenticate_with_api(client)

        document1_upload = (
            client.post("/document", json={"name": document_path1.name})
            .raise_for_status()
            .json()
        )
        document2_upload = (
            client.post("/document", json={"name": document_path2.name})
            .raise_for_status()
            .json()
        )

        documents_upload = (
            client.post(
                "/documents", json={"names": [document_path1.name, document_path2.name]}
            )
            .raise_for_status()
            .json()
        )

        assert (
            document1_upload["parameters"]["url"]
            == documents_upload[0]["parameters"]["url"]
        )
        assert (
            document2_upload["parameters"]["url"]
            == documents_upload[1]["parameters"]["url"]
        )

        assert (
            document1_upload["document"]["name"]
            == documents_upload[0]["document"]["name"]
        )
        assert (
            document2_upload["document"]["name"]
            == documents_upload[1]["document"]["name"]
        )

        # assuming that if test passes for first document it will also pass for the other
        with open(document_path1, "rb") as file:
            response_sequential_upload1 = client.request(
                document1_upload["parameters"]["method"],
                document1_upload["parameters"]["url"],
                data=document1_upload["parameters"]["data"],
                files={"file": file},
            )
            response_batch_upload1 = client.request(
                documents_upload[0]["parameters"]["method"],
                documents_upload[0]["parameters"]["url"],
                data=documents_upload[0]["parameters"]["data"],
                files={"file": file},
            )

        assert response_sequential_upload1.status_code == status.HTTP_200_OK
        assert response_batch_upload1.status_code == status.HTTP_200_OK

        assert (
            response_sequential_upload1.json()["name"]
            == response_batch_upload1.json()["name"]
        )
