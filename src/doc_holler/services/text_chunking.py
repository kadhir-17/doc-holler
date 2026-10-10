from dataclasses import dataclass

from doc_holler.integrations.document_extractors import ExtractedSection


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    document_id: str
    filename: str
    text: str
    chunk_index: int
    page_number: int | None = None


def validate_chunking_parameters(chunk_size_words: int, chunk_overlap_words: int) -> None:
    if chunk_size_words <= 0:
        raise ValueError("chunk_size_words must be greater than 0")
    if chunk_overlap_words < 0:
        raise ValueError("chunk_overlap_words must be greater than or equal to 0")
    if chunk_overlap_words >= chunk_size_words:
        raise ValueError("chunk_overlap_words must be less than chunk_size_words")


def split_words_with_overlap(
    words: list[str],
    chunk_size_words: int,
    chunk_overlap_words: int,
) -> list[str]:
    chunks: list[str] = []
    step = chunk_size_words - chunk_overlap_words
    start = 0
    total = len(words)

    while start < total:
        end = min(start + chunk_size_words, total)
        chunk_text = " ".join(words[start:end]).strip()
        if chunk_text:
            chunks.append(chunk_text)
        if end >= total:
            break
        start += step

    return chunks


def chunk_sections(
    document_id: str,
    filename: str,
    sections: list[ExtractedSection],
    chunk_size_words: int = 250,
    chunk_overlap_words: int = 40,
) -> list[TextChunk]:
    validate_chunking_parameters(chunk_size_words, chunk_overlap_words)

    chunks: list[TextChunk] = []
    global_index = 0

    for section in sections:
        cleaned_text = section.text.strip()
        if not cleaned_text:
            continue

        paragraphs = [p.strip() for p in cleaned_text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [cleaned_text]

        accumulated_words: list[str] = []

        for para in paragraphs:
            para_words = para.split()
            if not para_words:
                continue

            if len(accumulated_words) + len(para_words) <= chunk_size_words:
                accumulated_words.extend(para_words)
            else:
                if accumulated_words:
                    chunk_text = " ".join(accumulated_words).strip()
                    if chunk_text:
                        chunks.append(
                            TextChunk(
                                chunk_id=f"{document_id}_chunk_{global_index}",
                                document_id=document_id,
                                filename=filename,
                                text=chunk_text,
                                chunk_index=global_index,
                                page_number=section.page_number,
                            )
                        )
                        global_index += 1

                    overlap = (
                        accumulated_words[-chunk_overlap_words:] if chunk_overlap_words > 0 else []
                    )
                    accumulated_words = overlap + para_words
                else:
                    accumulated_words = para_words

                if len(accumulated_words) > chunk_size_words:
                    word_chunks = split_words_with_overlap(
                        accumulated_words, chunk_size_words, chunk_overlap_words
                    )
                    for idx, wc in enumerate(word_chunks):
                        if idx < len(word_chunks) - 1:
                            chunks.append(
                                TextChunk(
                                    chunk_id=f"{document_id}_chunk_{global_index}",
                                    document_id=document_id,
                                    filename=filename,
                                    text=wc,
                                    chunk_index=global_index,
                                    page_number=section.page_number,
                                )
                            )
                            global_index += 1
                        else:
                            accumulated_words = wc.split()

        if accumulated_words:
            chunk_text = " ".join(accumulated_words).strip()
            if chunk_text:
                chunks.append(
                    TextChunk(
                        chunk_id=f"{document_id}_chunk_{global_index}",
                        document_id=document_id,
                        filename=filename,
                        text=chunk_text,
                        chunk_index=global_index,
                        page_number=section.page_number,
                    )
                )
                global_index += 1

    return chunks
