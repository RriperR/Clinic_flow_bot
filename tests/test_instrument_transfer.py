from app.application.instruments.transfer_use_case import InstrumentTransferService
from app.domain.entities import Cabinet, Instrument, InstrumentMove


class FakeCabinetRepository:
    def __init__(self, cabinets: list[Cabinet]):
        self.cabinets = {cabinet.id: cabinet for cabinet in cabinets}

    async def list_all(self, include_archived: bool = False):
        return list(self.cabinets.values())

    async def get_by_id(self, cabinet_id: int):
        return self.cabinets.get(cabinet_id)


class FakeInstrumentRepository:
    def __init__(self, instruments: list[Instrument]):
        self.instruments = {instrument.id: instrument for instrument in instruments}

    async def get_by_id(self, instrument_id: int):
        return self.instruments.get(instrument_id)

    async def update_cabinet(self, instrument_id: int, cabinet_id: int) -> bool:
        instrument = self.instruments.get(instrument_id)
        if not instrument:
            return False
        instrument.cabinet_id = cabinet_id
        return True


class FakeMoveRepository:
    def __init__(self):
        self.moves: list[InstrumentMove] = []

    async def get_last_for_instrument(self, instrument_id: int):
        for move in reversed(self.moves):
            if move.instrument_id == instrument_id:
                return move
        return None

    async def add(self, move: InstrumentMove) -> None:
        self.moves.append(move)


async def test_transfer_from_sterilization_updates_cabinet_and_records_move() -> None:
    source = Cabinet(id=1, name="Cabinet", is_active=True)
    sterilization = Cabinet(id=2, name=InstrumentTransferService.STERILIZATION_CABINET_NAME, is_active=True)
    instrument = Instrument(id=10, name="Probe", cabinet_id=source.id, is_active=True)
    moves = FakeMoveRepository()
    service = InstrumentTransferService(
        FakeCabinetRepository([source, sterilization]),
        FakeInstrumentRepository([instrument]),
        moves,
    )

    moved_to_sterilization = await service.transfer_instrument(
        instrument.id,
        source.id,
        sterilization.id,
        "before",
        "after",
        "1",
    )
    moved_back = await service.transfer_instrument(
        instrument.id,
        sterilization.id,
        source.id,
        "before-back",
        "after-back",
        "1",
    )

    assert moved_to_sterilization is True
    assert moved_back is True
    assert instrument.cabinet_id == source.id
    assert len(moves.moves) == 2
