"""Pumble integration (helpdesk/integrations/pumble.py), tested against
stand-ins for frappe and requests - no bench, no network.

The parts that matter most are covered here: customer-written text can never
ping the team or inject a link, the server only ever calls Pumble's own host,
channels only receive the events and scope they asked for, and every Pumble
response (success, rate limit, error, network failure) is handled."""

import importlib.util
import re
import sys
import types
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "helpdesk/integrations/pumble.py"

CHANNELS: list = []
ENQUEUED: list = []
POSTS: list = []
RESPONSES: list = []


class Row(dict):
	__getattr__ = dict.get


class FakeResponse:
	def __init__(self, status_code, text=""):
		self.status_code, self.text = status_code, text


class RequestException(Exception):
	pass


def _get_all(doctype, filters=None, fields=None, **_):
	assert doctype == "HD Pumble Channel", doctype
	return [
		Row(c) for c in CHANNELS if all(c.get(k) == v for k, v in (filters or {}).items())
	]


def _post(url, json=None, timeout=None):
	POSTS.append(json)
	response = RESPONSES.pop(0)
	if isinstance(response, Exception):
		raise response
	return response


def _load():
	frappe = types.ModuleType("frappe")
	utils = types.ModuleType("frappe.utils")
	utils.strip_html = lambda s: re.sub(r"<[^>]+>", "", s)
	utils.get_url = lambda: "https://support.example.com"
	utils.now_datetime = lambda: None
	utils.add_to_date = lambda *a, **k: None
	utils.format_datetime = lambda *a, **k: ""
	frappe.utils = utils
	frappe.get_all = _get_all
	frappe.enqueue = lambda method, **kw: ENQUEUED.append((method, kw))
	frappe.log_error = lambda *a, **k: None
	frappe.flags = types.SimpleNamespace(initial_sync=False)
	requests = types.ModuleType("requests")
	requests.post = _post
	requests.RequestException = RequestException

	saved = {k: sys.modules.get(k) for k in ("frappe", "frappe.utils", "requests")}
	sys.modules.update({"frappe": frappe, "frappe.utils": utils, "requests": requests})
	try:
		spec = importlib.util.spec_from_file_location("pumble_under_test", MODULE)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		# The module keeps its own references; don't leak the stand-ins.
		for name, original in saved.items():
			if original is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = original
	module.time = types.SimpleNamespace(sleep=lambda s: None)  # no real waiting
	return module


pumble = _load()


class TestSafe(unittest.TestCase):
	def test_mentions_cannot_ping(self):
		for raw in ("@channel urgent", "@here now", "hi <<@U123>>", "<<#C1>> <<&G1>>"):
			out = pumble.safe(raw)
			self.assertNotIn("@channel", out)
			self.assertNotIn("@here", out)
			self.assertNotIn("<<", out)
			self.assertNotIn(">>", out)

	def test_links_cannot_be_injected(self):
		for raw in (
			"[click](https://evil.example)",
			"<https://evil.example|click>",
			'<a href="https://evil.example">click</a>',
		):
			out = pumble.safe(raw)
			self.assertNotIn("](", out)
			self.assertNotIn("<", out)
			self.assertNotIn("|click>", out)

	def test_markdown_cannot_restyle(self):
		out = pumble.safe("**bold** `code` ~~gone~~")
		for char in "*`~":
			self.assertNotIn(char, out)

	def test_one_line_and_html_stripped(self):
		self.assertEqual(pumble.safe("<p>Hello</p>\n\n  <b>world</b>"), "Hello world")

	def test_truncates_with_ellipsis(self):
		out = pumble.safe("x" * 500, 50)
		self.assertEqual(len(out), 50)
		self.assertTrue(out.endswith("…"))

	def test_empty(self):
		self.assertEqual(pumble.safe(None), "")


class TestReplyText(unittest.TestCase):
	def test_drops_quoted_history(self):
		self.assertEqual(
			pumble.reply_text("Thanks, that worked. On Mon, 4 Oct 2026 at 10:00 John wrote: > old"),
			"Thanks, that worked.",
		)

	def test_drops_outlook_original_message(self):
		self.assertEqual(pumble.reply_text("Done. -----Original Message----- From: x"), "Done.")

	def test_keeps_text_when_marker_is_at_the_start(self):
		self.assertTrue(pumble.reply_text("From: me - all good").startswith("From:"))


class TestValidWebhook(unittest.TestCase):
	def test_accepts_pumble(self):
		self.assertTrue(
			pumble.valid_webhook(
				"https://api.pumble.com/workspaces/abc/incomingWebhooks/postMessage/xyz"
			)
		)

	def test_rejects_anything_else(self):
		for url in (
			None,
			"",
			"http://api.pumble.com/x",
			"https://api.pumble.com.evil.example/x",
			"https://evil.example/?u=https://api.pumble.com/",
			"https://api.pumble.com/x y",
			"https://api.pumble.com/x\n",
		):
			with self.subTest(url=url):
				self.assertFalse(pumble.valid_webhook(url))


class TestRouting(unittest.TestCase):
	def setUp(self):
		base = {"enabled": 1, "on_new_ticket": 1, "project": None, "customer": None, "email_account": None}
		CHANNELS[:] = [
			{**base, "name": "all"},
			{**base, "name": "luuka", "project": "P-LUUKA"},
			{**base, "name": "finance-inbox", "email_account": "finance@"},
			{**base, "name": "client-x", "customer": "Client X"},
			{**base, "name": "switched-off", "enabled": 0},
			{**base, "name": "no-tickets", "on_new_ticket": 0},
		]
		ENQUEUED.clear()

	def test_scope_and_event_filtering(self):
		self.assertEqual(sorted(pumble.channels_for("new_ticket")), ["all"])
		self.assertEqual(
			sorted(pumble.channels_for("new_ticket", project="P-LUUKA")), ["all", "luuka"]
		)
		self.assertEqual(
			sorted(pumble.channels_for("new_ticket", email_account="finance@")),
			["all", "finance-inbox"],
		)
		self.assertEqual(
			sorted(pumble.channels_for("new_ticket", project="P-LUUKA", customer="Client X")),
			["all", "client-x", "luuka"],
		)

	def test_notify_queues_after_commit_on_the_short_queue(self):
		pumble.notify("new_ticket", "hello", project="P-LUUKA", reference=["HD Ticket", "T1"])
		self.assertEqual(sorted(kw["channel"] for _, kw in ENQUEUED), ["all", "luuka"])
		for method, kw in ENQUEUED:
			self.assertEqual(method, "helpdesk.integrations.pumble.deliver")
			self.assertTrue(kw["enqueue_after_commit"])
			self.assertEqual(kw["queue"], "short")
			self.assertEqual(kw["text"], "hello")


class TestPost(unittest.TestCase):
	URL = "https://api.pumble.com/workspaces/a/incomingWebhooks/postMessage/b"

	def setUp(self):
		POSTS.clear()
		RESPONSES.clear()

	def test_success(self):
		RESPONSES.append(FakeResponse(200))
		self.assertIsNone(pumble.post(self.URL, "hi"))
		self.assertEqual(POSTS, [{"text": "hi"}])

	def test_retries_once_when_rate_limited(self):
		RESPONSES.extend([FakeResponse(429), FakeResponse(200)])
		self.assertIsNone(pumble.post(self.URL, "hi"))
		self.assertEqual(len(POSTS), 2)

	def test_gives_up_after_a_second_rate_limit(self):
		RESPONSES.extend([FakeResponse(429), FakeResponse(429)])
		self.assertIn("429", pumble.post(self.URL, "hi"))

	def test_reports_server_errors(self):
		RESPONSES.append(FakeResponse(500, "boom"))
		error = pumble.post(self.URL, "hi")
		self.assertIn("500", error)
		self.assertIn("boom", error)

	def test_reports_network_errors(self):
		RESPONSES.append(RequestException("timed out"))
		self.assertIn("timed out", pumble.post(self.URL, "hi"))

	def test_truncates_to_pumbles_limit(self):
		RESPONSES.append(FakeResponse(200))
		pumble.post(self.URL, "x" * 15000)
		self.assertEqual(len(POSTS[0]["text"]), 10000)


if __name__ == "__main__":
	unittest.main()
