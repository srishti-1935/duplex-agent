from schemas import Event, EventType


def png_to_text_event(source_event: Event) -> Event:
    """
    Takes a video_frame Event, returns a new text_chunk Event.
    Stubbed for now — replace the fake description with a real vision call later.
    """
    fake_description = "stub description from image"
    return Event(
        type=EventType.TEXT_CHUNK,
        text=fake_description,
        is_end_of_turn=True,
    )