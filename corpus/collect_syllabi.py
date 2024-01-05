import csv
import io
import json
import logging
from http.client import HTTPResponse
from pathlib import Path
from typing import Optional
from urllib import parse, request

logger = logging.getLogger(__name__)


class KdbsyllabiCollector(object):
    BASE_SEARCH_FORM = {
        "_eventId": "",
        "index": "",
        "locale": "",
        "nendo": "",
        "termCode": "",
        "dayCode": "",
        "periodCode": "",
        "campusCode": "",
        "hierarchy1": "",
        "hierarchy2": "",
        "hierarchy3": "",
        "hierarchy4": "",
        "hierarchy5": "",
        "freeWord": "",
        "_orFlg": 1,
        "_andFlg": 1,
        "_gaiyoFlg": 1,
        "_syllabiFlg": 1,
        "_engFlg": 1,
        "_risyuFlg": 1,
        "_ryugakuFlg": 1,
        "_excludeFukaikoFlg": 1,
        "outputFormat": 1,
    }

    FIELD_MAP = {
        "科目番号": "subject_number",
        "科目名": "subject_name",
        "授業方法": "class_method",
        "単位数": "credit",
        "標準履修年次": "grade",
        "実施学期": "semester",
        "曜時限": "schedule",
        "教室": "classroom",
        "担当教員": "instructor",
        "授業概要": "overview",
        "備考": "note",
        "科目等履修生申請可否": "can_apply_for_subject",
        "申請条件": "application_condition",
        "短期留学生申請可否": "can_apply_for_short_term_study_abroad",
        "英語(日本語)科目名": "subject_name_en",
        "科目コード": "subject_code",
        "要件科目名": "required_subject_name",
        "データ更新日  ": "updated_at",
    }

    RequestReturn = tuple[HTTPResponse, bytes]

    def __init__(self, kdb_url: str, year: int) -> None:
        self.kdb_url = kdb_url
        self.year = year
        self.session = self.create_session(kdb_url)

    def _open(
        self,
        url: str,
        opener: request.OpenerDirector,
        data: Optional[dict] = None,
        method: str = "GET",
    ) -> RequestReturn:
        try:
            if data is not None and self._flowExecutionKey is not None:
                data["_flowExecutionKey"] = self._flowExecutionKey
            req = request.Request(
                url,
                data=None if data is None else parse.urlencode(data).encode("utf-8"),
                method=method,
            )
            logger.debug(f"Request url: {url}")
            logger.debug(f"Request data: {data}")

            with opener.open(req) as res:
                parsed_url = parse.urlparse(res.url)
                query_params = parse.parse_qs(parsed_url.query)
                if "_flowExecutionKey" in query_params:
                    self._flowExecutionKey = query_params["_flowExecutionKey"][0]

                return res, res.read()

        except request.HTTPError as e:
            logger.debug(f"Response: {e.read().decode('utf-8')}")
            raise Exception(f"HTTPError: {e.reason} ({e.code})")

    def create_session(self, url) -> tuple[request.OpenerDirector]:
        opener = request.build_opener(
            request.HTTPSHandler(debuglevel=1),
            request.HTTPCookieProcessor(),
        )
        res, body = self._open(url, opener)
        logger.debug("Session created")
        return opener

    @property
    def _search_url(self) -> str:
        return self.kdb_url + "campusweb/campussquare.do"

    def _search(self) -> RequestReturn:
        seed_request_data = self.BASE_SEARCH_FORM | {
            "_eventId": "searchOpeningCourse",
            "nendo": self.year,
        }
        return self._open(
            self._search_url, self.session, data=seed_request_data, method="POST"
        )

    def _download_csv(self, output_path: Path) -> RequestReturn:
        download_request_data = self.BASE_SEARCH_FORM | {
            "_eventId": "output",
            "nendo": self.year,
            "outputFormat": 0,
        }
        res, body = self._open(
            self._search_url, self.session, data=download_request_data, method="POST"
        )
        reader = csv.DictReader(io.StringIO(body.decode("cp932")))
        with output_path.open("w") as f:
            for line in reader:
                syllabi = {
                    self.FIELD_MAP[k]: v
                    for k, v in line.items()
                    if k in self.FIELD_MAP
                }
                f.write(json.dumps(syllabi, ensure_ascii=False) + "\n")

    def collect(self, output_path: Path):
        res, body = self._search()

        self._download_csv(output_path)


def main(year: int):
    KDB_URL = "https://kdb.tsukuba.ac.jp/"
    output_path = Path(__file__).parent.joinpath("syllabus.jsonl")

    collector = KdbsyllabiCollector(KDB_URL, year)
    collector.collect(output_path)


if __name__ == '__main__':
    year = 2023
    logging.basicConfig(level=logging.DEBUG)
    main(year)
