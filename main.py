import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import re
from scout import scout
# from scout_excel import process_excel

app = FastAPI()

# config
UPLOAD_DIR = "/home/site/wwwroot/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Home route
@app.get("/")
def home():
    return {"message": "Welcome to the Scout Crawler API"}

# Scout route
@app.get("/scout/{cas_or_name}")
async def run_scout(cas_or_name):
    if cas_or_name is None:
        return {"error": "No input provided."}

    # identify cas or name
    cas_pattern = r'^\d{2,7}-\d{2}-\d$'
    match = re.match(cas_pattern, cas_or_name)

    if bool(match):
        response = await scout(cas=cas_or_name, name=None)
    else:
        response = await scout(cas=None, name=cas_or_name)

    return JSONResponse(content=response)

'''
# Scout with excel
@app.post("/scout/excel")
async def run_scout_excel(file: UploadFile):
    file_location = ""
    try:
        if file is None:
            return {"error": "Excel file expected."}

        ext = file.filename.split(".")[-1]

        if ext != "xlsx":
            return {"error": f"Received {ext} file, excel file expected."}

        # save file to the uploads directory
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_location, "wb") as f:
            contents = await file.read()
            f.write(contents)

        # process excel file
        await process_excel(file_location)

        return {"filename": file.filename}

    except Exception as e:
        # report to the user and delete the created file
        os.remove(file_location)
        print("An occurred during excel processing: ", str(e))
        return {"error": str(e)}
'''

# Test write permission route
@app.get("/test-write-permission")
async def test_write_permission():
    test_file_path = os.path.join(UPLOAD_DIR, "testfile.txt")
    try:
        with open(test_file_path, "w") as test_file:
            test_file.write("This is a test.")
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            return {"message": "Write permission verified successfully."}
        else:
            return {"message": "Write permission test failed. File was not created."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Write permission test failed: {e}")
