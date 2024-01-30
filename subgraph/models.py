from pydantic import BaseModel


class Account(BaseModel):
    id: str


class Market(BaseModel):
    id: str


class Position(BaseModel):
    id: str
    createdAtTimestamp: str
    mint: str
    market: Market


class PositionForBuild(BaseModel):
    currentOi: str
    fractionUnwound: str


class PositionForUnwind(BaseModel):
    market: Market


class Build(BaseModel):
    id: str
    timestamp: str
    collateral: str
    position: PositionForBuild
    owner: Account


class Unwind(BaseModel):
    id: str
    mint: str
    position: PositionForUnwind
    timestamp: str


class Liquidate(BaseModel):
    id: str
    mint: str
    position: PositionForUnwind
    timestamp: str
