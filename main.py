import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel

from fotla.fotla.backend.api import start_api
from fotla.fotla.backend.corpus_loader import (
    AdhocCorpusLoader,
    Doc,
    JsonlCorpusLoader,
    Preprocessor,
)
from fotla.fotla.backend.encoder import HFSymetricDenseEncoder

# from fotla.backend.indexer.elasticsearch import (
#     ElasticsearchConfig,
#     ElasticsearchIndexer,
# )
# from fotla.backend.retriever import DenseRetriever
from fotla.fotla.backend.indexer.elasticsearch import (
    ElasticsearchBM25,
    ElasticsearchConfig,
    ElasticsearchIndexer,
)
from fotla.fotla.backend.retriever import DenseRetriever

# syllabi_attr: Dict[str, str] = {
#     "subject_number": (str, ...),
#     "subject_name": (str, ...),
#     "class_method": (str, ...),
#     "credit": (str, ...),
#     "grade": (str, ...),
#     "semester": (str, ...),
#     "schedule": (str, ...),
#     "classroom": (str, ...),
#     "instructor": (str, ...),
#     "overview": (str, ...),
#     "note": (str, ...),
#     # "can_apply_for_subject": (bool, ...),
#     "application_condition": (str, ...),
#     # "can_apply_for_short_term_study_abroad": (bool, ...),
#     "subject_name_en": (str, ...),
#     "subject_code": (str, ...),
#     "required_subject_name": (str, ...),
#     "updated_at": (datetime, ...),
# }


class Syllabi(BaseModel):
    subject_number: str
    subject_name: str
    class_method: str
    credit: Optional[str]
    grade: str
    semester: str
    schedule: str
    classroom: str
    instructor: str
    overview: str
    note: str
    # can_apply_for_subject: bool
    application_condition: str
    # can_apply_for_short_term_study_abroad: bool
    subject_name_en: str
    subject_code: str
    required_subject_name: str
    updated_at: datetime


def syllabi_preprocesser(syllabi: Syllabi) -> Syllabi:
    if syllabi.credit == "-":
        syllabi.credit = None


class SyllabiPreprocessor(Preprocessor):
    def __call__(self, syllabi: Syllabi) -> Syllabi:
        if syllabi.credit == "-":
            syllabi.credit = None
        return syllabi


def load_indexer(recreate_index: bool = False):
    es_host = os.environ.get("ELASTICSEARCH_HOST", "localhost")
    es_port = os.environ.get("ELASTICSEARCH_PORT", 9200)
    es_config = ElasticsearchConfig(
        es_host,
        es_port,
        index_name="kdb",
        index_scheme_path="mappings/kdb.json",
    )
    indexer = ElasticsearchIndexer(
        es_config,
        fields=list(Syllabi.model_fields.keys()),
        recreate_index=recreate_index,
    )
    return indexer


def load_retirever(indexer):
    def sillabi_to_text(docs: List[Doc]) -> List[str]:
        return [
            " ".join(
                [doc.subject_number, doc.subject_name, doc.overview, doc.instructor]
            )
            for doc in docs
        ]

    encoder = HFSymetricDenseEncoder("facebook/mcontriever-msmarco")
    retriever = DenseRetriever(encoder, indexer, model_to_texts=sillabi_to_text)
    # retriever = ElasticsearchBM25(indexer)

    return retriever


def index(retriever):
    corpus_loader = JsonlCorpusLoader(
        "corpus/syllabus.jsonl",
        data_type=Syllabi,
        preprocessores=[SyllabiPreprocessor()],
    )

    retriever.index(corpus_loader)


def main(args):
    indexer = load_indexer(args.recreate_index)
    retriever = load_retirever(indexer)

    if args.index:
        index(retriever)

    if not args.retrieve == "":
        search_fields = [
            "subject_number",
            "subject_name",
        ]
        results = retriever.retrieve(
            [args.retrieve], 100, search_fields=search_fields
        )
        print(json.dumps(results, indent=2))
    else:
        start_api(retriever, port=9999)


def parse_args():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--index", action="store_true")
    parser.add_argument("--retrieve", default="")
    parser.add_argument("--recreate_index", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    # logging.basicConfig(level=logging.WARNING)
    args = parse_args()
    main(args)
