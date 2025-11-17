from fastapi import APIRouter


router = APIRouter(prefix="reports")



router.post("/")
def create_report():
    pass

router.get("/")
def list_reports():
    pass

router.get("/{report_id}")
def get_report_by_id():
    pass

