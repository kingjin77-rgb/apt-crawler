from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Session
from datetime import datetime
import os

class Base(DeclarativeBase):
    pass

class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)           # 출처 (청약홈, LH, SH 등)
    announce_id = Column(String(100))                     # 원본 공고 ID
    title = Column(String(500), nullable=False)           # 공고명
    housing_type = Column(String(50))                     # 주택유형 (아파트/오피스텔 등)
    region_sido = Column(String(50))                      # 시도
    region_sigungu = Column(String(100))                  # 시군구
    region_address = Column(Text)                         # 전체 주소
    supply_count = Column(Integer)                        # 공급세대수
    recruitment_start = Column(String(20))                # 청약접수 시작일
    recruitment_end = Column(String(20))                  # 청약접수 종료일
    announce_date = Column(String(20))                    # 공고일
    winner_date = Column(String(20))                      # 당첨자 발표일
    move_in_date = Column(String(20))                     # 입주예정일
    min_price = Column(Integer)                           # 최저 분양가 (만원)
    max_price = Column(Integer)                           # 최고 분양가 (만원)
    url = Column(String(1000))                            # 공고문 URL
    content = Column(Text)                                # 공고문 전문
    raw_data = Column(Text)                               # 원본 JSON
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("source", "announce_id", name="uq_source_announce"),
    )


def get_engine(db_path: str):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", echo=False)


def init_db(db_path: str):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine


def upsert_announcement(engine, data: dict) -> bool:
    """공고 저장 (중복 시 업데이트). 새 레코드면 True 반환."""
    with Session(engine) as session:
        existing = session.query(Announcement).filter_by(
            source=data.get("source"),
            announce_id=data.get("announce_id"),
        ).first()

        if existing:
            for k, v in data.items():
                if hasattr(existing, k):
                    setattr(existing, k, v)
            existing.updated_at = datetime.now()
            session.commit()
            return False
        else:
            obj = Announcement(**{k: v for k, v in data.items() if hasattr(Announcement, k)})
            session.add(obj)
            session.commit()
            return True
