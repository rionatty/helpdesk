# Knowledge-base suggestions without RediSearch.
#
# Article suggestions (the box under the subject when a customer opens a new
# ticket) run on RediSearch - a module that ships with Redis Stack, not with
# the plain Redis a bench installs. Without it the search quietly returned
# nothing, so the feature looked finished but never suggested anything.
#
# This is the fallback: a plain database search over published articles,
# shaped exactly like the RediSearch results so the same box renders it.

import html
import re

import frappe
from frappe.utils import strip_html

MAX_WORDS = 6
STOPWORDS = {
	"the", "and", "for", "with", "not", "can", "cannot", "how", "what", "why",
	"when", "where", "who", "are", "was", "were", "has", "have", "had", "does",
	"did", "but", "you", "your", "our", "this", "that", "these", "those", "from",
	"into", "about", "there", "their", "they", "them", "its", "any", "all", "get",
	"got", "will", "would", "could", "should", "please", "help", "need", "issue",
	"problem", "able", "unable", "via", "per",
}


def words_of(query) -> list:
	"""Distinct search words: 3+ characters, not a stopword, at most six."""
	out = []
	for word in re.findall(r"[a-z0-9]+", (query or "").lower()):
		if len(word) >= 3 and word not in STOPWORDS and word not in out:
			out.append(word)
	return out[:MAX_WORDS]


def score(title, text, words) -> int:
	"""A word in the title counts three times a word in the body."""
	title, text = (title or "").lower(), (text or "").lower()
	return sum(3 * (w in title) + (w in text) for w in words)


def snippet(text, words, width: int = 180) -> str:
	"""Excerpt around the first match, with matches in <b>. The suggestion box
	renders this with v-html, so every piece of article text is escaped; the
	text is split on the matches first, so bolding can never land inside an
	escaped entity (a search for "amp" must not touch "&amp;")."""
	text = " ".join((text or "").split())
	low = text.lower()
	hits = [i for i in (low.find(w) for w in words) if i >= 0]
	start = max(0, min(hits) - 40) if hits else 0
	part = text[start : start + width]
	pieces = re.split(
		"(" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + ")",
		part,
		flags=re.IGNORECASE,
	) if words else [part]
	body = "".join(
		f"<b>{html.escape(p)}</b>" if i % 2 else html.escape(p) for i, p in enumerate(pieces)
	)
	return ("…" if start > 0 else "") + body + ("…" if start + width < len(text) else "")


def rank(rows, words) -> list:
	"""Best match first; among equals, the most recently updated."""
	rows = sorted(rows, key=lambda r: str(r.get("modified") or ""), reverse=True)
	return sorted(rows, key=lambda r: score(r.get("title"), r.get("text"), words), reverse=True)


def db_search(query, limit: int) -> list:
	words = words_of(query)
	if not words:
		return []
	or_filters = [["title", "like", f"%{w}%"] for w in words] + [
		["content", "like", f"%{w}%"] for w in words
	]
	rows = frappe.get_all(
		"HD Article",
		filters={"status": "Published"},
		or_filters=or_filters,
		fields=["name", "title", "content", "category", "modified"],
		limit_page_length=50,
	)
	if not rows:
		return []
	for r in rows:
		r["text"] = strip_html(r.get("content") or "")
	categories = {
		c.name: c.category_name
		for c in frappe.get_all(
			"HD Article Category",
			filters={"name": ["in", list({r.category for r in rows if r.get("category")})]},
			fields=["name", "category_name"],
		)
	} if any(r.get("category") for r in rows) else {}
	return [
		{
			"id": f"HD Article:{r.name}",
			"doctype": "HD Article",
			# The box links to name.split("#")[0] and uses the part after "#"
			# as a section anchor; a whole-article match opens at the top.
			"name": f"{r.name}#",
			"subject": r.title,
			"headings": categories.get(r.get("category")) or "",
			"description": snippet(r["text"], words),
			"modified": r.get("modified"),
		}
		for r in rank(rows, words)[:limit]
	]
