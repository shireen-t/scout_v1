import os
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import re
from scout import scout
#from scout_excel import process_excel

app = FastAPI()

# config
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


#Home route
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
		print("An occured during excel processing : ", str(e))
		return {"error": str(e)}
'''