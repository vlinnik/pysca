import os
import sys
from dataclasses import dataclass,field
from pathlib import Path
from typing import List
from types import ModuleType

from sqlalchemy import String,Boolean,BLOB,Integer,create_engine,select,or_,exc,__version__ as sqlalchemy_version
from sqlalchemy.orm import Session,Mapped

@dataclass
class Config():
    workdir     : Path = field(default_factory=lambda: Path.cwd().resolve())
    workspace   : Path = field(default_factory=lambda: Path('.') )
    ui          : Path = field(default_factory=lambda: Path('ui') )
    widgets     : Path = field(default_factory=lambda: Path('widgets') )
    modules     : List[Path] = field(default_factory=lambda: [Path('.')])
    plugins     : List[Path] = field(default_factory=lambda: [Path('.')]+[Path(p) for p in sys.path] )
    resources   : List[Path] = field(default_factory=lambda: [Path('.')] )
    db          : Path = field(default_factory=lambda: Path('default.scada'))
    logics      : Path = field(default_factory=lambda: Path('.'))
    imported    : List[ModuleType] = field(default_factory=lambda: [])  #загруженные модули
    
    def __post_init__(self):
        self.workdir = Path(self.workdir).expanduser().resolve()
        self.workspace = self.workdir.joinpath(Path(self.workspace).expanduser()).resolve()
        self.ui   = self.workdir.joinpath(Path(self.ui).expanduser()).resolve()
        self.widgets = self.workdir.joinpath(Path(self.widgets).expanduser()).resolve()
        self.modules = [self.workdir.joinpath(Path(p).expanduser()).resolve() for p in self.modules]
        self.plugins = [self.workdir.joinpath(Path(p).expanduser()).resolve() for p in self.plugins]
        self.db   = self.workdir.joinpath(Path(self.db).expanduser()).resolve()
        self.resources = [self.workdir.joinpath(Path(p).expanduser()).resolve() for p in self.resources]
        self.logics = self.workspace.joinpath(Path(self.logics).expanduser()).resolve()

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
