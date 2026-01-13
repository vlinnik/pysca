import os
import sys
from dataclasses import dataclass,field
from pathlib import Path
from typing import List

from sqlalchemy import String,Boolean,BLOB,Integer,create_engine,select,or_,exc,__version__ as sqlalchemy_version
from sqlalchemy.orm import Session,Mapped

@dataclass
class Config():
    workspace   : Path = field(default_factory=lambda: Path.cwd().resolve() )
    ui          : Path = field(default_factory=lambda: Path('ui') )
    widgets     : Path = field(default_factory=lambda: Path('widgets') )
    modules     : List[Path] = field(default_factory=lambda: [Path.cwd().resolve()])
    plugins     : List[Path] = field(default_factory=lambda: [Path.cwd()]+[Path(p) for p in sys.path] )
    resources   : List[Path] = field(default_factory=lambda: [Path.cwd()] )
    db          : Path = field(default_factory=lambda: Path('default.scada'))
    logics      : Path = field(default_factory=lambda: Path.cwd().resolve())
    
    def __post_init__(self):
        self.workspace = Path(self.workspace).expanduser().absolute()
        self.ui   = Path(self.ui).expanduser().absolute()
        self.widgets = Path(self.widgets).expanduser().absolute()
        self.modules = [Path(p).expanduser().resolve() for p in self.modules]
        self.plugins = [Path(p).expanduser().resolve() for p in self.plugins]
        self.db   = Path(self.db).expanduser().absolute()
        self.resources = [Path(p).expanduser().resolve() for p in self.resources]
        self.logics = Path(self.logics).expanduser().resolve()

#работа с базой конфигурации проекта
if sqlalchemy_version<'2':
    from sqlalchemy import Column as mapped_column
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()
else:
    from sqlalchemy.orm import mapped_column,DeclarativeBase
    class Base(DeclarativeBase):
        pass

class Variables(Base):
    __tablename__ = "Variables"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(45))
    type: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(45))
    comment: Mapped[str] = mapped_column(String(45))
    address: Mapped[str] = mapped_column(String(128))
    logging: Mapped[bool] = mapped_column(Boolean)
    events: Mapped[bool] = mapped_column(Boolean)
    alarms: Mapped[bool] = mapped_column(Boolean)
    properties: Mapped[BLOB] = mapped_column(BLOB)

class Animations(Base):
    __tablename__ = "Animations"
    id: Mapped[int] = mapped_column(primary_key=True)
    objectID: Mapped[str] = mapped_column(String(128))
    className: Mapped[str] = mapped_column(String(45))
    prop: Mapped[str] = mapped_column('property',String(45))
    data: Mapped[str] = mapped_column(String(128))

class Signals(Base):
    __tablename__ = "Signals"
    id: Mapped[int] = mapped_column(primary_key=True)
    objectID: Mapped[str] = mapped_column(String(128))
    className: Mapped[str] = mapped_column(String(45))
    signal: Mapped[str] = mapped_column(String(45))
    data: Mapped[str] = mapped_column(String(128))
