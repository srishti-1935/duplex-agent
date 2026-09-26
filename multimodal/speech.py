from schemas import Event, EventType


def wav_to_text_event(source_event: Event) -> Event:
    """
    Takes an audio_wav Event, returns a new text_chunk Event.
    Stubbed for now — replace the fake transcript with a real STT call later.
    """
    fake_transcript = "stub transcript from audio"
    return Event(
        type=EventType.TEXT_CHUNK,
        text=fake_transcript,
        is_end_of_turn=True,
    )