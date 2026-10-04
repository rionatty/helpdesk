"""WhatsApp channel (helpdesk/integrations/whatsapp.py): the pure parts -
webhook signatures, reading Meta's message shapes, ticket subjects, turning
an agent's HTML reply into WhatsApp text, splitting long replies, the
24-hour window and the acknowledgement's rate limit - tested without a
bench, a network or Meta."""

import hashlib
import hmac
import importlib.util
import sys
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "helpdesk/integrations/whatsapp.py"


def _load():
	frappe = types.ModuleType("frappe")
	frappe._ = lambda s: s
	frappe.whitelist = lambda *a, **k: (lambda f: f)
	utils = types.ModuleType("frappe.utils")
	utils.cint = lambda v: int(float(v or 0))
	for name in ("add_to_date", "get_datetime", "now_datetime"):
		setattr(utils, name, lambda *a, **k: None)
	frappe.utils = utils
	requests = types.ModuleType("requests")
	requests.RequestException = type("RequestException", (Exception,), {})
	pypika = types.ModuleType("pypika")
	pypika_functions = types.ModuleType("pypika.functions")
	pypika_functions.Replace = lambda *a: None
	werkzeug = types.ModuleType("werkzeug")
	wrappers = types.ModuleType("werkzeug.wrappers")
	wrappers.Response = object
	stand_ins = {
		"frappe": frappe,
		"frappe.utils": utils,
		"requests": requests,
		"pypika": pypika,
		"pypika.functions": pypika_functions,
		"werkzeug": werkzeug,
		"werkzeug.wrappers": wrappers,
	}
	saved = {k: sys.modules.get(k) for k in stand_ins}
	sys.modules.update(stand_ins)
	try:
		spec = importlib.util.spec_from_file_location("whatsapp_under_test", MODULE)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		for name, original in saved.items():
			if original is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = original
	return module


wa = _load()


class TestSignature(unittest.TestCase):
	SECRET = "app-secret"
	BODY = b'{"object":"whatsapp_business_account"}'

	def sign(self, body, secret=SECRET):
		return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

	def test_genuine(self):
		self.assertTrue(wa.verify_signature(self.SECRET, self.BODY, self.sign(self.BODY)))

	def test_tampered_body(self):
		self.assertFalse(wa.verify_signature(self.SECRET, self.BODY + b" ", self.sign(self.BODY)))

	def test_other_secret(self):
		self.assertFalse(wa.verify_signature(self.SECRET, self.BODY, self.sign(self.BODY, "guess")))

	def test_nothing_is_trusted_without_a_secret_or_header(self):
		self.assertFalse(wa.verify_signature("", self.BODY, self.sign(self.BODY, "")))
		self.assertFalse(wa.verify_signature(self.SECRET, self.BODY, None))
		self.assertFalse(wa.verify_signature(self.SECRET, self.BODY, self.sign(self.BODY)[7:]))


class TestParseMessage(unittest.TestCase):
	def test_text(self):
		self.assertEqual(
			wa.parse_message({"type": "text", "text": {"body": " Invoice won't post "}}),
			("text", "Invoice won't post", None),
		)

	def test_photo_with_caption(self):
		kind, text, media = wa.parse_message(
			{"type": "image", "image": {"id": "M1", "mime_type": "image/jpeg", "caption": "Error"}}
		)
		self.assertEqual((kind, text, media), ("image", "[Photo] Error", ("M1", "image/jpeg", None)))

	def test_document_keeps_its_name(self):
		kind, text, media = wa.parse_message(
			{"type": "document", "document": {"id": "M2", "mime_type": "application/pdf", "filename": "inv.pdf"}}
		)
		self.assertEqual(text, "[Document: inv.pdf]")
		self.assertEqual(media, ("M2", "application/pdf", "inv.pdf"))

	def test_voice_note(self):
		self.assertEqual(
			wa.parse_message({"type": "audio", "audio": {"id": "M3", "mime_type": "audio/ogg"}})[1],
			"[Voice message]",
		)

	def test_location(self):
		text = wa.parse_message(
			{"type": "location", "location": {"latitude": -1.28, "longitude": 36.82, "name": "Office"}}
		)[1]
		self.assertEqual(text, "[Location] -1.28, 36.82 (Office)")

	def test_contact_card(self):
		text = wa.parse_message(
			{"type": "contacts", "contacts": [{"name": {"formatted_name": "Ann"}, "phones": [{"phone": "+254700"}]}]}
		)[1]
		self.assertEqual(text, "[Contact card] Ann +254700")

	def test_buttons(self):
		self.assertEqual(
			wa.parse_message({"type": "interactive", "interactive": {"button_reply": {"title": "Yes"}}})[1], "Yes"
		)
		self.assertEqual(wa.parse_message({"type": "button", "button": {"text": "Stop"}})[1], "Stop")

	def test_a_reaction_carries_no_words(self):
		self.assertEqual(wa.parse_message({"type": "reaction", "reaction": {"emoji": "👍"}}), ("reaction", "", None))
		self.assertIn("reaction", wa.SILENT_TYPES)


class TestSubjectAndBody(unittest.TestCase):
	def test_first_line(self):
		self.assertEqual(wa.ticket_subject("\nPrinter down\nsince 9am", "Ann", "254700"), "Printer down")

	def test_long_line_is_cut(self):
		subject = wa.ticket_subject("x" * 300, "Ann", "254700")
		self.assertEqual(len(subject), 140)
		self.assertTrue(subject.endswith("..."))

	def test_media_only(self):
		self.assertEqual(wa.ticket_subject("[Photo]", "Ann", "254700"), "WhatsApp message from Ann")
		self.assertEqual(wa.ticket_subject("", None, "254700"), "WhatsApp message from +254700")

	def test_body_is_escaped(self):
		self.assertEqual(
			wa.message_html("<script>x</script>\nline 2"),
			"<p>&lt;script&gt;x&lt;/script&gt;<br>line 2</p>",
		)


class TestHtmlToWhatsApp(unittest.TestCase):
	def test_paragraphs_and_emphasis(self):
		self.assertEqual(
			wa.html_to_whatsapp("<p>Hello <strong>Ann</strong>,</p><p>It is <em>fixed</em>.</p>"),
			"Hello *Ann*,\n\nIt is _fixed_.",
		)

	def test_quoted_history_is_left_out(self):
		self.assertEqual(
			wa.html_to_whatsapp(
				'<p>Done.</p><p class="reply-to-content"></p><blockquote><p>Old message</p></blockquote>'
			),
			"Done.",
		)

	def test_lists(self):
		self.assertEqual(wa.html_to_whatsapp("<ul><li>One</li><li>Two</li></ul>"), "• One\n• Two")
		self.assertEqual(wa.html_to_whatsapp("<ol><li>One</li><li>Two</li></ol>"), "1. One\n2. Two")

	def test_links_keep_their_address(self):
		self.assertEqual(
			wa.html_to_whatsapp('<p>See <a href="https://kb.example.com/a">this</a></p>'),
			"See this (https://kb.example.com/a)",
		)
		self.assertEqual(
			wa.html_to_whatsapp('<p><a href="https://kb.example.com">https://kb.example.com</a></p>'),
			"https://kb.example.com",
		)

	def test_entities_breaks_and_empty_tags(self):
		self.assertEqual(
			wa.html_to_whatsapp("<p>A&amp;B&nbsp;now<br>next<strong></strong></p>"), "A&B now\nnext"
		)


class TestSplitText(unittest.TestCase):
	def test_short_text_is_one_message(self):
		self.assertEqual(wa.split_text("Hello"), ["Hello"])

	def test_long_text_is_cut_at_paragraphs(self):
		paragraphs = [("p%d " % i) * 300 for i in range(10)]
		parts = wa.split_text("\n\n".join(paragraphs), limit=4096)
		self.assertGreater(len(parts), 1)
		self.assertTrue(all(len(p) <= 4096 for p in parts))
		self.assertEqual(" ".join(" ".join(parts).split()), " ".join(" ".join(paragraphs).split()))

	def test_one_endless_word_is_cut_hard(self):
		parts = wa.split_text("x" * 9000, limit=4096)
		self.assertEqual([len(p) for p in parts], [4096, 4096, 808])

	def test_empty(self):
		self.assertEqual(wa.split_text("  "), [])


class TestWindowAndTemplate(unittest.TestCase):
	NOW = datetime(2026, 10, 5, 12, 0)

	def test_window(self):
		self.assertFalse(wa.within_window(None, self.NOW))
		self.assertTrue(wa.within_window(self.NOW - timedelta(hours=23), self.NOW))
		self.assertFalse(wa.within_window(self.NOW - timedelta(hours=25), self.NOW))

	def test_template_text_is_one_short_line(self):
		self.assertEqual(wa.template_text("Line one\n\n\tLine   two"), "Line one Line two")
		cut = wa.template_text("word " * 400, limit=100)
		self.assertEqual(len(cut), 100)
		self.assertTrue(cut.endswith("…"))


class TestRateLimit(unittest.TestCase):
	LIMITS = ((3600, 2), (86400, 3))

	def test_allows_up_to_the_limit_then_refuses(self):
		states, now = {}, 1000.0
		results = []
		for _ in range(3):
			allowed, states = wa.check_windows(states, now, self.LIMITS)
			results.append(allowed)
		self.assertEqual(results, [True, True, False])

	def test_the_hour_resets_but_the_day_still_counts(self):
		states, now = {}, 1000.0
		for _ in range(2):
			_, states = wa.check_windows(states, now, self.LIMITS)
		allowed, states = wa.check_windows(states, now + 3601, self.LIMITS)
		self.assertTrue(allowed)
		allowed, states = wa.check_windows(states, now + 3602, self.LIMITS)
		self.assertFalse(allowed)  # three today already

	def test_a_refusal_does_not_count(self):
		states = {3600: {"start": 0.0, "count": 2}, 86400: {"start": 0.0, "count": 2}}
		allowed, after = wa.check_windows(states, 10.0, self.LIMITS)
		self.assertFalse(allowed)
		self.assertEqual(after, states)


class TestAcknowledgement(unittest.TestCase):
	def test_default(self):
		self.assertEqual(
			wa.render_ack(None, "123", "Ann Wanjiku"),
			"Thanks, Ann! We have your message and opened ticket #123. We will reply here as soon as we can.",
		)

	def test_without_a_name(self):
		self.assertTrue(wa.render_ack(None, "123", None).startswith("Thanks! We have"))

	def test_custom_and_broken_templates(self):
		self.assertEqual(wa.render_ack("Ticket {ticket} open{name}.", "9", "Ann"), "Ticket 9 open, Ann.")
		self.assertIn("ticket #9", wa.render_ack("Hi {customer}", "9", "Ann"))


class TestDigits(unittest.TestCase):
	def test_digits(self):
		self.assertEqual(wa.digits("+254 (712) 345-678"), "254712345678")
		self.assertEqual(wa.digits(None), "")


if __name__ == "__main__":
	unittest.main()
