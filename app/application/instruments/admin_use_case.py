from app.domain.entities import Cabinet, Instrument
from app.domain.repositories import (
    CabinetRepository,
    InstrumentMoveRepository,
    InstrumentRepository,
)


class InstrumentAdminService:
    def __init__(
        self,
        cabinets: CabinetRepository,
        instruments: InstrumentRepository,
        moves: InstrumentMoveRepository,
    ):
        self.cabinets = cabinets
        self.instruments = instruments
        self.moves = moves

    async def list_cabinets(self, include_archived: bool = False):
        return list(await self.cabinets.list_all(include_archived=include_archived))

    async def get_cabinet(self, cabinet_id: int):
        return await self.cabinets.get_by_id(cabinet_id)

    async def add_cabinet(self, name: str) -> None:
        cabinet = Cabinet(id=None, name=name, is_active=True)
        await self.cabinets.add(cabinet)

    async def rename_cabinet(self, cabinet_id: int, name: str) -> bool:
        return await self.cabinets.update_name(cabinet_id, name)

    async def set_cabinet_active(self, cabinet_id: int, is_active: bool) -> bool:
        return await self.cabinets.set_active(cabinet_id, is_active)

    async def delete_cabinet(self, cabinet_id: int) -> bool:
        has_items = await self.cabinets.has_instruments(cabinet_id)
        if has_items:
            return False
        return await self.cabinets.delete(cabinet_id)

    async def list_instruments(self, cabinet_id: int, include_archived: bool = False):
        return list(await self.instruments.list_by_cabinet(cabinet_id, include_archived=include_archived))

    async def get_instrument(self, instrument_id: int):
        return await self.instruments.get_by_id(instrument_id)

    async def add_instrument(self, cabinet_id: int, name: str) -> None:
        instrument = Instrument(id=None, name=name, cabinet_id=cabinet_id, is_active=True)
        await self.instruments.add(instrument)

    async def rename_instrument(self, instrument_id: int, name: str) -> bool:
        return await self.instruments.update_name(instrument_id, name)

    async def set_instrument_active(self, instrument_id: int, is_active: bool) -> bool:
        return await self.instruments.set_active(instrument_id, is_active)

    async def delete_instrument(self, instrument_id: int) -> bool:
        return await self.instruments.delete(instrument_id)

    async def list_recent_moves(self, limit: int = 20):
        return list(await self.moves.list_recent(limit=limit))

    async def get_move(self, move_id: int):
        return await self.moves.get_by_id(move_id)
