import re

import frappe
from textblob import TextBlob
from textblob.exceptions import MissingCorpusError

from helpdesk.search import NUM_RESULTS
from helpdesk.search import search as hd_search


def get_nouns(blob: TextBlob):
    try:
        return [word for word, pos in blob.pos_tags if pos[0] == "N"]
    except LookupError:
        return []


def get_noun_phrases(blob: TextBlob):
    try:
        return blob.noun_phrases
    except (LookupError, MissingCorpusError):
        return []


def search_with_enough_results(
    prev_res: list, query: str, qtype="and"
) -> tuple[list, bool]:
    out = hd_search(query, qtype=qtype)
    if not out:
        return prev_res, len(prev_res) == NUM_RESULTS
    items = prev_res + out[0].get("items", [])
    items = list({v["id"]: v for v in items}.values())[:NUM_RESULTS]  # unique results
    return items, len(items) == NUM_RESULTS


def sanitize_query(query: str) -> str:
    q = query.strip().lower()
    q = re.sub(r"[^a-z0-9\s]", " ", q)
    # Collapse multiple spaces into one
    q = re.sub(r"\s+", " ", q)
    return q.strip()


@frappe.whitelist()
def get_article_stats(article_name: str):
    views = frappe.db.get_value("HD Article", article_name, "views")

    likes = frappe.db.count(
        "HD Article Feedback",
        filters={
            "article": article_name,
            "feedback": 1,
        },
    )

    dislikes = frappe.db.count(
        "HD Article Feedback",
        filters={
            "article": article_name,
            "feedback": 2,
        },
    )

    return {
        "views": views,
        "likes": likes,
        "dislikes": dislikes,
    }


@frappe.whitelist()
def search(query: str) -> list:
    query = sanitize_query(query)
    if not query:
        return []
    try:
        return _search(query)
    except Exception:
        # KB article suggestions are best-effort. If the search backend is
        # unavailable (e.g. the RediSearch module isn't installed or the
        # index hasn't been built) never bubble a 500 up to the customer's
        # ticket form — just return no suggestions. Log once per hour so the
        # root cause stays diagnosable without flooding the Error Log on every
        # keystroke.
        if not frappe.cache().get_value("hd_article_search_error_logged"):
            frappe.log_error(title="Helpdesk article search failed")
            frappe.cache().set_value(
                "hd_article_search_error_logged", True, expires_in_sec=3600
            )
        return []


def _search(query: str) -> list:
    ret, enough = search_with_enough_results([], query)
    if enough:
        return ret
    blob = TextBlob(query)  # fallback
    if noun_phrases := get_noun_phrases(blob):
        query = " ".join(noun_phrases)
        ret, enough = search_with_enough_results(ret, query)
        if enough:
            return ret
        ret, enough = search_with_enough_results(ret, query, qtype="or")
        if enough:
            return ret
    if nouns := get_nouns(blob):
        query = " ".join(nouns)
        ret, enough = search_with_enough_results(ret, query)
        if enough:
            return ret
        ret, enough = search_with_enough_results(ret, query, qtype="or")
    return ret
