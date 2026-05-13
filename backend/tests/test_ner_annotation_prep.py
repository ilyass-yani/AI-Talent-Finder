from scripts.prepare_ner_annotations import prepare_annotations, spans_to_bio, normalize_spans


def test_prepare_template_annotations():
    records = [{"text": "Python developer at ACME"}]

    prepared = prepare_annotations(records, mode="template")

    assert prepared[0]["tokens"] == ["Python", "developer", "at", "ACME"]
    assert prepared[0]["ner_tags"] == ["O", "O", "O", "O"]


def test_convert_spans_to_bio_tags():
    text = "Senior Python developer at ACME"
    spans = normalize_spans([
        {"start": 7, "end": 13, "label": "SKILL"},
        {"start": 27, "end": 31, "label": "ORG"},
    ])

    prepared = spans_to_bio(text, spans)

    assert prepared["tokens"] == ["Senior", "Python", "developer", "at", "ACME"]
    assert prepared["ner_tags"][1] == "B-SKILL"
    assert prepared["ner_tags"][4] == "B-ORG"