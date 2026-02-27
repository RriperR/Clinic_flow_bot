from datetime import datetime

from app.domain.entities import InstrumentMove
from app.domain.repositories import (
    CabinetRepository,
    InstrumentRepository,
    InstrumentMoveRepository,
)
from app.text_utils import normalize_text


class InstrumentTransferService:
    STERILIZATION_CABINET_NAME = "Стерилизационная"

    def __init__(
        self,
        cabinets: CabinetRepository,
        instruments: InstrumentRepository,
        moves: InstrumentMoveRepository,
    ):
        self.cabinets = cabinets
        self.instruments = instruments
        self.moves = moves

    async def list_cabinets(self):
        return list(await self.cabinets.list_all())

    async def get_cabinet(self, cabinet_id: int):
        return await self.cabinets.get_by_id(cabinet_id)

    async def get_sterilization_cabinet(self):
        cabinets = await self.cabinets.list_all()
        for cabinet in cabinets:
            if (
                cabinet.name
                and normalize_text(cabinet.name)
                == normalize_text(self.STERILIZATION_CABINET_NAME)
            ):
                return cabinet
        return None

    async def list_instruments(self, cabinet_id: int):
        return list(await self.instruments.list_by_cabinet(cabinet_id))

    async def get_instrument(self, instrument_id: int):
        return await self.instruments.get_by_id(instrument_id)

    async def get_last_move_for_instrument(self, instrument_id: int):
        return await self.moves.get_last_for_instrument(instrument_id)

    async def transfer_instrument(
        self,
        instrument_id: int,
        from_cabinet_id: int,
        to_cabinet_id: int,
        before_photo_id: str,
        after_photo_id: str,
        moved_by_chat_id: str,
    ) -> bool:
        if from_cabinet_id == to_cabinet_id:
            return False

        instrument = await self.instruments.get_by_id(instrument_id)
        if not instrument or instrument.cabinet_id != from_cabinet_id:
            return False

        target = await self.cabinets.get_by_id(to_cabinet_id)
        if not target:
            return False

        sterilization = await self.get_sterilization_cabinet()
        if not sterilization:
            return False
        if from_cabinet_id == sterilization.id:
            last_move = await self.moves.get_last_for_instrument(instrument_id)
            if last_move and last_move.to_cabinet_id == sterilization.id:
                if last_move.from_cabinet_id != to_cabinet_id:
                    return False
        else:
            if to_cabinet_id != sterilization.id:
                return False

        updated = await self.instruments.update_cabinet(instrument_id, to_cabinet_id)
        if not updated:
            return False

        moved_at = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        move = InstrumentMove(
            id=None,
            instrument_id=instrument_id,
            from_cabinet_id=from_cabinet_id,
            to_cabinet_id=to_cabinet_id,
            before_photo_id=before_photo_id,
            after_photo_id=after_photo_id,
            moved_by_chat_id=moved_by_chat_id,
            moved_at=moved_at,
        )
        await self.moves.add(move)
        return True
