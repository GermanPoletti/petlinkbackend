from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select
from models import Report, User
from models.post.post import Post
from schemas import ReportCreate, ReportRead
from exceptions import ReportNotFoundException, ReportAlreadyReviewedException
from services import post_service


def create_report(session: Session, payload: ReportCreate, user_id: int):
    report_data = payload.model_dump(exclude_unset=True)
    new_report = Report(reporting_user_id=user_id, **report_data)

    session.add(new_report)
    session.commit()
    session.refresh(new_report)

    return ReportRead.model_validate(new_report, from_attributes=True)

def get_all_reports(session: Session):
    reports = session.execute(
        select(Report).join(Report.post).filter(
            Report.is_reviewed == False,
            Post.is_active == True
        )
    ).scalars().all()

    return [ReportRead.model_validate(r, from_attributes=True) for r in reports]


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

    # Get author before deleting the post
    post = session.get(Post, report.post_id)
    post_author_id = post.user_id if post else None

    post_service.delete_post(session=session, post_id=report.post_id, user=user)

    report.is_reviewed = True
    all_reports = session.exec(select(Report).where(Report.post_id == report.post_id)).all()
    for r in all_reports:
        r.is_reviewed = True

    # Apply warning and optional ban to the post author
    if post_author_id:
        author = session.get(User, post_author_id)
        if author:
            author.warnings = (author.warnings or 0) + 1
            if author.warnings >= 3:
                author.banned_until = datetime.now(timezone.utc) + timedelta(days=7)
                # Terminate their active session so the ban takes effect immediately
                from services.auth_service import terminate_active_session
                terminate_active_session(session, author.id)  # type: ignore
            session.add(author)

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
