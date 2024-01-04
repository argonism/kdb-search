import os
from datetime import datetime
from typing import Dict, List

from fotla.fotla.backend.api import start_api
from fotla.fotla.backend.corpus_loader import AdhocCorpusLoader, Doc, JsonlCorpusLoader
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

import pydantic


syllabi_attr: Dict[str, str] = {
    "subject_number" : "str",
    "subject_name" : "str",
    "class_method" : "str",
    "credit" : "str",
    "grade" : "str",
    "semester" : "str",
    "schedule" : "str",
    "classroom" : "str",
    "instructor" : "str",
    "overview" : "str",
    "note" : "str",
    "can_apply_for_subject" : "str",
    "application_condition" : "str",
    "can_apply_for_short_term_study_abroad" : "str",
    "subject_name_en" : "str",
    "subject_code" : "str",
    "required_subject_name" : "str",
    "updated_at" : "str",
}

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
        fields=list(syllabi_attr.keys()),
        recreate_index=recreate_index,
    )
    return indexer


def load_retirever(indexer):
    # encoder = HFSymetricDenseEncoder("facebook/mcontriever-msmarco")
    # retriever = DenseRetriever(encoder, indexer)
    retriever = ElasticsearchBM25(indexer)

    return retriever


def index(retriever):
    Syllabi = pydantic.create_model("Syllabi", **syllabi_attr)

    corpus_loader = JsonlCorpusLoader(
        "corpus/syllabus.100.jsonl",
        data_type=Syllabi,
    )

    retriever.async_index(corpus_loader)


def main(args):
    indexer = load_indexer(args.recreate_index)
    retriever = load_retirever(indexer)

    if args.index:
        index(retriever)

    if not args.retrieve == "":
        results = retriever.retrieve([args.retrieve], 100)
        print(results)
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
    args = parse_args()
    main(args)
