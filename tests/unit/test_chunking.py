import pytest

from doc_holler.integrations.document_extractors import ExtractedSection
from doc_holler.services.text_chunking import chunk_sections, validate_chunking_parameters


def test_validate_chunking_parameters() -> None:
    with pytest.raises(ValueError):
        validate_chunking_parameters(0, 10)
    with pytest.raises(ValueError):
        validate_chunking_parameters(100, -5)
    with pytest.raises(ValueError):
        validate_chunking_parameters(100, 100)
    with pytest.raises(ValueError):
        validate_chunking_parameters(50, 60)


def test_chunking_short_text() -> None:
    sections = [ExtractedSection(text="A quick test of chunking.", page_number=1)]
    chunks = chunk_sections(
        "doc1", "sample.pdf", sections, chunk_size_words=50, chunk_overlap_words=10
    )
    assert len(chunks) == 1
    assert chunks[0].document_id == "doc1"
    assert chunks[0].filename == "sample.pdf"
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].text == "A quick test of chunking."


def test_chunking_preserves_page_numbers() -> None:
    sections = [
        ExtractedSection(text="Page one words here.", page_number=1),
        ExtractedSection(text="Page two different words here.", page_number=2),
    ]
    chunks = chunk_sections(
        "doc1", "sample.pdf", sections, chunk_size_words=20, chunk_overlap_words=5
    )
    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert chunks[1].page_number == 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1


def test_chunking_long_text_with_overlap() -> None:
    long_words = [f"word{i}" for i in range(120)]
    text = " ".join(long_words)
    sections = [ExtractedSection(text=text, page_number=None)]
    chunks = chunk_sections(
        "doc2", "notes.txt", sections, chunk_size_words=50, chunk_overlap_words=10
    )

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text.split()) <= 50
        assert chunk.text.strip() != ""
        assert chunk.document_id == "doc2"

    first_chunk_words = chunks[0].text.split()
    second_chunk_words = chunks[1].text.split()
    assert first_chunk_words[-10:] == second_chunk_words[:10]


def test_chunking_empty_sections() -> None:
    sections = [
        ExtractedSection(text="   ", page_number=1),
        ExtractedSection(text="", page_number=2),
    ]
    chunks = chunk_sections("doc3", "empty.pdf", sections)
    assert chunks == []
