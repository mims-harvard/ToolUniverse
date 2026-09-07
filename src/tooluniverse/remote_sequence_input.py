"""Validation helpers for public biological-sequence remote tools."""


def validate_sequence(value, *, name, alphabet, max_length):
    """Return one normalized sequence with strict alphabet and length bounds."""
    if not isinstance(value, str):
        raise ValueError(f"'{name}' must be a string.")
    sequence = value.strip().upper()
    if not sequence:
        raise ValueError(f"'{name}' must not be empty.")
    if len(sequence) > max_length:
        raise ValueError(
            f"'{name}' must contain at most {max_length} characters."
        )
    invalid = set(sequence) - set(alphabet)
    if invalid:
        raise ValueError(f"'{name}' contains unsupported sequence characters.")
    return sequence


def validate_variant_sequences(
    ref_value,
    alt_value,
    *,
    alphabet,
    max_length,
):
    """Validate a same-length reference/alternate sequence pair."""
    ref = validate_sequence(
        ref_value, name="ref_sequence", alphabet=alphabet, max_length=max_length
    )
    alt = validate_sequence(
        alt_value, name="alt_sequence", alphabet=alphabet, max_length=max_length
    )
    if len(ref) != len(alt):
        raise ValueError("'ref_sequence' and 'alt_sequence' must have equal length.")
    return ref, alt


def validate_track_selection(
    track_indices,
    top_n,
    *,
    n_tracks,
    max_items=1000,
):
    """Validate bounded explicit track indices or a bounded top-N selection."""
    if top_n is None:
        top_n = 20
    if type(top_n) is not int or not 1 <= top_n <= min(max_items, n_tracks):
        raise ValueError(
            f"'top_n' must be an integer from 1 to {min(max_items, n_tracks)}."
        )

    if track_indices is None:
        return None, top_n
    if not isinstance(track_indices, list) or not 1 <= len(
        track_indices
    ) <= max_items:
        raise ValueError(
            f"'track_indices' must contain 1 to {max_items} integers."
        )
    if any(
        type(index) is not int or not 0 <= index < n_tracks
        for index in track_indices
    ):
        raise ValueError(
            f"'track_indices' entries must be integers from 0 to {n_tracks - 1}."
        )
    if len(set(track_indices)) != len(track_indices):
        raise ValueError("'track_indices' must not contain duplicates.")
    return track_indices, top_n
