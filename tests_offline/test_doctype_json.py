"""Every doctype definition is well-formed - checked here, before
`bench migrate` trips over a broken one on the server."""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCTYPES = sorted(
	p
	for p in (ROOT / "helpdesk").glob("**/doctype/*/*.json")
	if p.stem == p.parent.name
)
NEEDS_OPTIONS = ("Link", "Table", "Table MultiSelect")


class TestDoctypeJson(unittest.TestCase):
	def test_found_doctypes(self):
		self.assertGreater(len(DOCTYPES), 0, "no doctype JSON found - wrong path?")

	def test_each_doctype(self):
		for path in DOCTYPES:
			with self.subTest(doctype=path.parent.name):
				meta = json.loads(path.read_text(encoding="utf-8"))
				self.assertEqual(meta.get("doctype"), "DocType")
				self.assertTrue(meta.get("name"))

				fields = meta.get("fields", [])
				names = [f.get("fieldname") for f in fields]
				self.assertTrue(all(names), "a field has no fieldname")
				self.assertEqual(len(names), len(set(names)), "duplicate fieldname")

				order = meta.get("field_order")
				if order is not None:
					self.assertEqual(set(order), set(names), "field_order out of step with fields")

				for f in fields:
					kind = f.get("fieldtype")
					if kind in NEEDS_OPTIONS:
						self.assertTrue(f.get("options"), f"{f['fieldname']}: {kind} needs options")
					if kind == "Select" and f.get("default") not in (None, ""):
						self.assertIn(
							str(f["default"]),
							(f.get("options") or "").split("\n"),
							f"{f['fieldname']}: default is not one of the options",
						)


if __name__ == "__main__":
	unittest.main()
