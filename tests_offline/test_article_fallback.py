"""Knowledge-base suggestions without RediSearch
(helpdesk/api/article_fallback.py) - tested without a bench."""

import importlib.util
import re
import sys
import types
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "helpdesk/api/article_fallback.py"
ARTICLES: list = []


class Row(dict):
	__getattr__ = dict.get


def _get_all(doctype, filters=None, or_filters=None, **_):
	if doctype == "HD Article Category":
		return [Row(name="cat-1", category_name="Accounts")]
	rows = [Row(a) for a in ARTICLES if a.get("status") == "Published"]
	if or_filters:
		def hit(row):
			return any(
				pattern.strip("%").lower() in (row.get(field) or "").lower()
				for field, _op, pattern in or_filters
			)
		rows = [r for r in rows if hit(r)]
	return rows


def _load():
	frappe = types.ModuleType("frappe")
	frappe.get_all = _get_all
	utils = types.ModuleType("frappe.utils")
	utils.strip_html = lambda s: re.sub(r"<[^>]+>", "", s)
	frappe.utils = utils
	saved = {k: sys.modules.get(k) for k in ("frappe", "frappe.utils")}
	sys.modules.update({"frappe": frappe, "frappe.utils": utils})
	try:
		spec = importlib.util.spec_from_file_location("article_fallback_under_test", MODULE)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		for name, original in saved.items():
			if original is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = original
	return module


af = _load()


class TestWords(unittest.TestCase):
	def test_drops_short_words_stopwords_and_repeats(self):
		self.assertEqual(
			af.words_of("How do I reset my password? reset PASSWORD on the app"),
			["reset", "password", "app"],
		)

	def test_caps_at_six_words(self):
		self.assertEqual(len(af.words_of("one two three four five six seven eight nine")), 6)


class TestSnippet(unittest.TestCase):
	def test_escapes_article_html_and_bolds_matches(self):
		out = af.snippet("Click <script>alert(1)</script> to reset", ["reset"])
		self.assertNotIn("<script>", out)
		self.assertIn("&lt;script&gt;", out)
		self.assertIn("<b>reset</b>", out)

	def test_bolding_never_breaks_an_entity(self):
		out = af.snippet("Tom & Jerry amp", ["amp"])
		self.assertIn("&amp;", out)  # the escaped "&" is intact...
		self.assertIn("<b>amp</b>", out)  # ...and only the real word is bolded
		self.assertNotIn("&<b>", out)

	def test_excerpt_centres_on_the_match(self):
		out = af.snippet("x " * 200 + "invoice posting" + " y" * 200, ["invoice"])
		self.assertTrue(out.startswith("…") and out.endswith("…"))
		self.assertIn("<b>invoice</b>", out)


class TestSearch(unittest.TestCase):
	def setUp(self):
		ARTICLES[:] = [
			{"name": "a1", "title": "Reset your password", "content": "<p>Use the link.</p>",
			 "status": "Published", "category": "cat-1", "modified": "2026-01-01"},
			{"name": "a2", "title": "Printing", "content": "<p>To reset the printer...</p>",
			 "status": "Published", "category": None, "modified": "2026-06-01"},
			{"name": "a3", "title": "Reset everything", "content": "draft",
			 "status": "Draft", "category": None, "modified": "2026-09-01"},
		]

	def test_title_matches_rank_first_and_drafts_never_show(self):
		results = af.db_search("reset password", 5)
		self.assertEqual([r["id"] for r in results], ["HD Article:a1", "HD Article:a2"])

	def test_results_have_the_shape_the_suggestion_box_renders(self):
		top = af.db_search("password", 5)[0]
		self.assertEqual(top["subject"], "Reset your password")
		self.assertEqual(top["name"].split("#")[0], "a1")
		self.assertEqual(top["headings"], "Accounts")
		self.assertIn("doctype", top)

	def test_nothing_searchable_returns_nothing(self):
		self.assertEqual(af.db_search("how do I", 5), [])


if __name__ == "__main__":
	unittest.main()
