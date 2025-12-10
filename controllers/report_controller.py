from fastapi import APIRouter, Depends, HTTPException, status

from core.database import SessionDep
from dependencies.auth_dependencies import get_current_user
from exceptions import ReportNotFoundException, ReportAlreadyReviewedException
from models.post.report import Report
from models.user.user import User
from services import report_service

from dependencies.permissions_dependencies import require_role
from models.enums import RoleEnum
from schemas import ReportCreate, ReportRead
from utils.generics import count_rows

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/count")
def reports_count(session: SessionDep, current_user: User = require_role(RoleEnum.ADMIN)):
    filters = {
        "is_reviewed": False
    }
    return count_rows(session=session, model= Report, filter_conditions=filters)


@router.post("/")
def create_report(session: SessionDep, report_data: ReportCreate, current_user: User = Depends(get_current_user)):
    assert current_user.id is not None
    return report_service.create_report(session=session, payload=report_data, user_id=current_user.id)
    
@router.get("/", response_model=list[ReportRead])
def list_reports(session: SessionDep, current_user: User = require_role(RoleEnum.MODERATOR)):
    try:
        return report_service.get_all_reports(session= session)
    except ReportNotFoundException as e:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/{report_id}")
def get_report_by_id(report_id: int, session: SessionDep, current_user: User = require_role(RoleEnum.MODERATOR)):
    try:
        return report_service.get_report_by_id(session = session, report_id = report_id)
    except ReportNotFoundException as e:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail=str(e))
    
#aca capturar ReportNotFoundException code 404 y ReportAlreadyReviewedException code 409
@router.post("/{report_id}/approve")
def approve_report(session: SessionDep, report_id: int, current_user: User = require_role(RoleEnum.MODERATOR)):
    try:    
        return report_service.approve_report(session = session, report_id=report_id, user= current_user)
    except ReportNotFoundException as e:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReportAlreadyReviewedException as e:
        raise HTTPException(status_code = status.HTTP_409_CONFLICT, detail=str(e))
    

@router.post("/{report_id}/dismiss")
def dismiss_report(session: SessionDep, report_id:int, current_user: User = require_role(RoleEnum.MODERATOR)):
    try:    
        return report_service.dismiss_report(session=session, report_id= report_id, user = current_user)
    except ReportNotFoundException as e:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReportAlreadyReviewedException as e:
        raise HTTPException(status_code = status.HTTP_409_CONFLICT, detail=str(e))
    
