import httpx
from fastapi import UploadFile

CATBOX_API = "https://catbox.moe/user/api.php"
LITTLEBOX_API = "https://litterbox.catbox.moe/resources/internals/api.php"

async def upload_to_catbox(file: UploadFile) -> str:
    file_content = await file.read()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            CATBOX_API,
            files={"fileToUpload": (file.filename, file_content)},
            data={"reqtype": "fileupload"}
        )

    if response.status_code == 200:
        return response.text.strip()
    else:
        raise RuntimeError(f"Error subiendo archivo a Catbox: {response.status_code}")
