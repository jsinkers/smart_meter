from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.orm import sessionmaker, relationship

from config import database_uri

Base = declarative_base()


class Nem12Record200(Base):
    __tablename__ = "Nem12Record200"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nmi = Column(Integer, nullable=False)
    meter_serial_num = Column(String)
    units_of_measure = Column(String)
    interval_length = Column(Integer)       # interval in minutes
    nem12_300_records = relationship("Nem12Record300")

    def add_record300(self, **kwargs):
        kwargs["record_200_id"] = self.id
        rec = Nem12Record300(**kwargs)
        session.add(rec)
        session.commit()
        return session.query(Nem12Record300).filter_by(update_datetime=rec.update_datetime).first()


class Nem12Record300(Base):
    __tablename__ = "Nem12Record300"
    id = Column(Integer, primary_key=True, autoincrement=True)
    record_200_id = Column(Integer, ForeignKey("Nem12Record200.id"), nullable=False)
    quality_method = Column(String(3))
    reason_code = Column(Integer)
    reason_description = Column(String(240))
    update_datetime = Column(DateTime)
    msats_load_datetime = Column(DateTime)
    record_200 = relationship("Nem12Record200")
    energy_usage = relationship("EnergyUsage")

    def add_energy_usage(self, **kwargs):
        kwargs["record_300_id"] = self.id
        rec = EnergyUsage(**kwargs)
        session.add(rec)
        session.commit()
        return session.query(EnergyUsage).get(rec.id)


class EnergyUsage(Base):
    __tablename__ = "EnergyUsage"
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    energy_usage = Column(Float, nullable=False)
    record_300_id = Column(Integer, ForeignKey("Nem12Record300.id"), nullable=False)
    record_300 = relationship("Nem12Record300")


#class EnergyPrices(Base):
#    __tablename__ = "EnergyPrices"
#    id = Column(Integer, primary_key=True, nullable=False)
#    # TODO: expand this schema

engine = create_engine(database_uri, echo=True)
Base.metadata.create_all(bind=engine)

Session = sessionmaker(bind=engine)
session = Session()
