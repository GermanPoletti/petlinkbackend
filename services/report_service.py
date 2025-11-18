from sqlmodel import Session, select
from models import Report, User
from schemas import ReportCreate, ReportRead
from exceptions import ReportNotFoundException, ReportAlreadyReviewedException
from services import post_service


#TODO: modify database, add reviewed dates to report, maybe admin comment


def create_report(session: Session, payload: ReportCreate, user_id: int):
    report_data = payload.model_dump(exclude_unset=True)
    new_report = Report(reporting_user_id= user_id, **report_data)

    session.add(new_report)
    session.commit()
    session.refresh(new_report)

    return ReportRead.model_validate(new_report, from_attributes=True)

#TODO: Separate get_all in get all not reviewed and get all reviewed
def get_all_reports(session: Session):
    reports = session.exec(select(Report)).all()
    if not reports:
        raise ReportNotFoundException("Reports not found")

    return [
        ReportRead.model_validate(r, from_attributes=True) for r in reports
    ]


def get_report_by_id(session: Session, report_id: int):
    report = session.get(Report, report_id)

    if not report:
        raise ReportNotFoundException("Report not found")

    return ReportRead.model_validate(report, from_attributes=True)


def approve_report(session: Session, report_id: int, user: User):
    report = session.get(Report, report_id)

    if not report:
        raise ReportNotFoundException("Report not found")
    if report.is_reviewed:
        raise ReportAlreadyReviewedException("Report was already reviewed")

    post_id = report.post_id

    post_service.delete_post(session=session, post_id=post_id, user=user)
    report.is_reviewed = True

    session.commit()
    session.refresh(report)

    return ReportRead.model_validate(report, from_attributes=True)

def dismiss_report(session: Session, report_id: int, user: User):

    report = session.get(Report, report_id)

    if not report:
        raise ReportNotFoundException("Report not found")
    if report.is_reviewed:
        raise ReportAlreadyReviewedException("Report was already reviewed")

    report.is_reviewed = True

    session.commit()
    session.refresh(report)

    return ReportRead.model_validate(report, from_attributes=True)

